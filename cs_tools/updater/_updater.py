from dataclasses import dataclass
from typing import List
import contextlib
import subprocess as sp
import logging
import pathlib
import shutil
import site
import sys
import os

log = logging.getLogger(__name__)
IS_WINDOWS = sys.platform == "win32"
IS_MACOSX = sys.platform == "darwin"


class CSToolsVirtualEnvironment:
    """
    Manage the CS Tools virtual environment.
    """

    def __init__(self, find_links: pathlib.Path = None):
        self.venv_path = self.get_venv_path()
        self.find_links = find_links

    @property
    def exists(self) -> bool:
        return self.exe.exists()

    @property
    def config_directory_name(self) -> str:
        return os.environ.get("CS_TOOLS_CONFIG_DIRNAME", "cs_tools")

    @property
    def exe(self) -> pathlib.Path:
        """Get the Python executable."""
        directory = "Scripts" if IS_WINDOWS else "bin"
        exec_name = "python.exe" if IS_WINDOWS else "python"
        return self.venv_path / directory / exec_name

    @staticmethod
    def run(*args, raise_on_failure: bool = True, **kwargs) -> sp.CompletedProcess:
        """Run a SHELL command."""
        levels = {"ERROR": log.error, "WARNING": log.warning}

        with sp.Popen(args, stdout=sp.PIPE, stderr=sp.STDOUT, **kwargs) as proc:
            for line_bytes in proc.stdout:
                line = line_bytes.decode().strip()

                if line.startswith("-----"):  # progressbar
                    continue

                elif line.startswith(tuple(levels)):
                    log_level, _, line = line.partition(": ")
                    logger = levels[log_level]

                else:
                    logger = log.debug

                logger(line)

        cp = sp.CompletedProcess(args, proc.returncode, stdout=proc.stdout, stderr=proc.stderr)

        if raise_on_failure and cp.returncode != 0:
            cmd = " ".join(args)
            raise RuntimeError(f"Failed with exit code: {cp.returncode}\n\nCOMMAND: {cmd}")

        return cp

    def get_venv_path(self) -> pathlib.Path:
        """Resolve to a User configuration directory."""
        if IS_WINDOWS:
            user_directory = pathlib.Path(os.environ.get("APPDATA", "~"))
        elif IS_MACOSX:
            user_directory = pathlib.Path("~/Library/Application Support")
        else:
            user_directory = pathlib.Path(os.environ.get("XDG_CONFIG_HOME", "~/.config"))

        return pathlib.Path(user_directory).expanduser() / self.config_directory_name / ".cs_tools"

    def python(self, *args, **kwargs) -> sp.CompletedProcess:
        """Run a command in the virtual environment."""
        return self.run(self.exe.as_posix(), *args, **kwargs)

    def pip(self, *args, **kwargs) -> sp.CompletedProcess:
        """Run a command in the virtual environment's pip."""
        # fmt: off
        required_general_args = (
            # ignore environment variables and user configuration
            "--isolated",
            # disable caching
            "--no-cache-dir",
            # don't ping for new versions of pip -- it doesn't matter and is noisy
            "--disable-pip-version-check",
            # trust installs from the official python package index
            "--trusted-host", "files.pythonhost.org",
            "--trusted-host", "pypi.org",
            "--trusted-host", "pypi.python.org",
        )
        # fmt: on

        if self.find_links is not None:
            required_general_args = (*required_general_args, "--find-links", self.find_links.as_posix())

        return self.python("-m", "pip", *required_general_args, *args, **kwargs)

    def make(self) -> None:
        """Create the virtual environment."""
        if self.exists:
            return

        self.venv_path.mkdir(parents=True, exist_ok=True)
        self.run(sys.executable, "-m", "venv", self.venv_path.as_posix())

        # Ensure `pip` is at least V20.3 so that backtracking is available
        self.pip("install", "pip>=20.3", "--upgrade")

    def reset(self) -> None:
        """Reset the virtual environment to base."""
        installed = self.venv_path.joinpath("INSTALLED-REQUIREMENTS.txt")
        installed.write_text(self.pip("freeze").stdout.decode())

        if installed.stat().st_size:
            self.pip("uninstall", "-r", installed.as_posix(), "-y")

        installed.unlink()


@dataclass
class FishPath:
    """
    fish's PATH is managed via the fish CLI.

    Further Reading:
      https://fishshell.com/docs/current/tutorial.html#path
    """

    venv: CSToolsVirtualEnvironment

    @property
    def bin_dir(self) -> pathlib.Path:
        return self.venv.exe.parent

    def add(self) -> None:
        # This is indempotent.
        log.info(f"Adding '{self.bin_dir}' to $fish_user_paths")
        sp.check_output(["fish_add_path", self.bin_dir.as_posix()])

    def unset(self) -> None:
        log.info(f"Removing '{self.bin_dir}' from $fish_user_paths")
        sp.check_output(["set", "PATH", f"(string match -v {self.bin_dir.as_posix()} $PATH)"])


@dataclass
class WindowsPath:
    """
    Window's PATH is best managed on the command line.
    """

    venv: CSToolsVirtualEnvironment

    @property
    def bin_dir(self) -> pathlib.Path:
        return self.venv.exe.parent

    @property
    def sys_py_dir(self) -> pathlib.Path:
        return pathlib.Path(site.getuserbase()) / "Scripts"

    def unlink_path(self, path: pathlib.Path) -> None:
        """
        Remove `path`.

        Compat py3.7 for missing_ok=True
        """
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    def symlink_paths(self, target_path: pathlib.Path, original_path: pathlib.Path) -> None:
        """Attempt to symlink in Windows."""
        self.unlink(target_path)

        try:
            log.info(f"Attempting to symlink: '{target_path}' -> '{original_path}'")
            target_path.symlink_to(original_path)

        # This can happen if the user does not have the correct permissions on Windows
        except OSError:
            log.info("Symlink failed, copying instead..")
            shutil.copy(original_path, target_path)

    def _broadcast(self) -> None:
        import ctypes

        # Tell other processes to update their environment
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x1A
        SMTO_ABORTIFHUNG = 0x0002

        result = ctypes.c_long()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            "Environment",
            SMTO_ABORTIFHUNG,
            5000,
            ctypes.byref(result),
        )

    @contextlib.contextmanager
    def win_registry(self):
        import winreg

        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as root:
            with winreg.OpenKey(root, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                yield key

    def add(self) -> None:
        import winreg

        with self.win_registry() as key:
            PATH, _ = winreg.QueryValueEx(key, "PATH")

            # Couldn't get PATH variable from registry, so we have to try to bruteforce
            # the path linking. First try to symlink, then just copy the damn thing.
            if PATH is None:
                self.symlink_paths(self.sys_py_dir / "cs_tools.exe", self.bin_dir / "cs_tools.exe")
                self.symlink_paths(self.sys_py_dir / "cstools.exe", self.bin_dir / "cstools.exe")
                return

            # Append to the PATH variable
            if self.bin_dir.as_posix() not in PATH:
                log.info(f"Adding '{self.bin_dir}' to User %PATH%")
                PATH = f"{PATH};{self.bin_dir.as_posix()}"
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, PATH)

        self._broadcast()

    def unset(self) -> None:
        import winreg

        with self.win_registry() as key:
            PATH, _ = winreg.QueryValueEx(key, "PATH")

            # Couldn't get the PATH variable from registry
            if PATH is None:
                self.unlink(self.sys_py_dir / "cs_tools.exe")
                self.unlink(self.sys_py_dir / "cstools.exe")
                return

            log.info(f"Removing '{self.bin_dir}' from User %PATH%")
            PATH = PATH.replace(f";{self.bin_dir.as_posix()}", "")
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, PATH)

        self._broadcast()


@dataclass
class UnixPath:
    """
    Modify SHELL profiles.

    base profile, zsh, and bash.
    """

    venv: CSToolsVirtualEnvironment

    @property
    def bin_dir(self) -> pathlib.Path:
        return self.venv.exe.parent

    @property
    def home(self) -> pathlib.Path:
        return pathlib.Path("~").expanduser()

    @property
    def profile_snippet(self) -> str:
        addition = (
            # fmt: off
            f"\n# absolute path to ThoughtSpot's CS Tools"
            # append to PATH (instead of prepend) in case of global python environment requiring common packages
            f'\nexport PATH="$PATH:{self.bin_dir}"'
            # If you are dealing with an environment where Python thinks you are restricted to ASCII data.
            # https://click.palletsprojects.com/en/8.1.x/unicode-support/
            f"\nexport LC_ALL=en_US.utf-8"
            f"\nexport LANG=en_US.utf-8"
            f"\n"
            # fmt: on
        )
        return addition

    def get_shell_profiles(self) -> List[pathlib.Path]:
        profiles = [self.home.joinpath(".profile")]

        if "zsh" in os.environ.get("SHELL", ""):
            zdotdir = pathlib.Path(os.getenv("ZDOTDIR", self.home))
            profiles.append(zdotdir.joinpath(".zprofile"))
            profiles.append(zdotdir.joinpath(".zshrc"))

        # .bash_profile is for login shells
        # .bashrc is for interactive shells
        for profile in [".bash_profile", ".bashrc"]:
            profiles.append(self.home.joinpath(profile))

        return profiles

    def add(self) -> None:
        for profile in self.get_shell_profiles():
            # don't write to profiles that don't exist
            if not profile.exists():
                continue

            if self.profile_snippet not in profile.read_text():
                log.info(f"Adding the '{self.bin_dir}' PATH snippet to {profile}")

                with profile.open(mode="a") as f:
                    f.write(self.profile_snippet)

    def unset(self) -> None:
        for profile in self.get_shell_profiles():
            if not profile.exists():
                continue

            contents = profile.read_text()

            if self.profile_snippet in contents:
                log.info(f"Removing the '{self.bin_dir}' PATH snippet from {profile}")
                contents = contents.replace(self.profile_snippet, "")

                with profile.open(mode="w") as f:
                    f.write(contents)
