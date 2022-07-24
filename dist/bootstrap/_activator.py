from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Tuple
import subprocess as sp
import logging
import shutil
import json
import os

from _virtual_env import VirtualEnvironment
from _errors import CSToolsActivatorError
from _const import HOME, PKGS, SHELL, VERSION_REGEX, WINDOWS
from _const import (
    POST_MESSAGE,
    POST_MESSAGE_NOT_IN_PATH,
    POST_MESSAGE_CONFIGURE_UNIX,
    POST_MESSAGE_CONFIGURE_FISH,
)
from _util import app_dir, bin_dir, compare_versions, http_get, entrypoints_from_whl


log = logging.getLogger(__name__)


class Activator:
    """
    The workhorse for bootstrapping our environment.

    Parameters
    ----------
    offline_install: bool [default, True]
      if True, leverage the packages directory /pkgs as the index server
      if False, ask GitHub for the latest install files

      (this should somehow callhome to let the project know that a user
       is updating their tools.. should think hard about how to enable
       this sanely)

    reinstall: bool [default, False]
      whether or not to rebuild the virtual environment

    setup: bool [default, False]
      whether or not to run any install code
    """

    def __init__(
        self,
        offline_install: bool = True,
        reinstall: bool = False,
        setup: bool = False
    ):
        self._offline_install = offline_install
        self._reinstall = reinstall
        self._setup = setup
        self._cs_tools_cfg_dir = app_dir("cs_tools")
        self._sys_exe_dir = bin_dir()

    @property
    def venv_dir(self) -> str:
        return self._cs_tools_cfg_dir.joinpath(".cs_tools")

    def run(self) -> int:
        log.info("Retrieving CS Tools metadata.")
        local, remote = self.get_versions()

        if compare_versions(local, remote) >= 0 and not self._reinstall:
            log.note("CS Tools is already up to date!")
            return 0

        # self._display_pre_message()
        self._ensure_directories()

        try:
            log.info(f"Installing CS Tools ({remote})")
            self._install(remote)
        except sp.CalledProcessError as e:
            raise CSToolsActivatorError(return_code=e.returncode, log=e.output.decode())
        else:
            log.info("Done!", extra={"parent": "install"})

        self._display_post_message(remote)
        return 0

    # def uninstall(self) -> int:
    #     ...

    def get_versions(self, version: str = None) -> Tuple[str, str]:
        # can expand ArgParser to this allow prerelase, or older version install
        if version is not None:
            return version

        local_version = "0.0.0"

        # retrieve for an existing install
        if self.venv_dir.exists():
            log.debug("found (.cs_tools) virtual environment", extra={"parent": "metadata"})
            env = VirtualEnvironment(self.venv_dir)
            cmd = "import cs_tools;print(cs_tools.__version__)"
            cp = env.python("-c", cmd, raise_on_failure=False)
            out = cp.stdout.decode().strip()

            if cp.returncode == 0:
                local_version = out
            else:
                log.debug(f"could not complete: {out}", extra={"parent": "metadata.venv"})

        log.debug(f"raw version -> {local_version}", extra={"parent": "metadata.venv"})

        if self._offline_install:
            log.debug("extracting version from cs_tools wheel", extra={"parent": "metadata"})
            try:
                fp = next(PKGS.glob("cs_tools*.whl"))
            except StopIteration as e:
                raise CSToolsActivatorError(return_code=1, log="offline installer contains no cs_tools wheel") from e
            # reliable because whl files have name conformity
            # <snake_case_pkg_name>-<version>-<platform-triplet>.whl
            # where platform triplet is <pyversion>-<abi>-<platform tag>
            # dots (.) in filename represent an OR relationship
            _, remote_version, *_ = fp.stem.split("-")
            log.debug(f"raw version -> {remote_version}", extra={"parent": "metadata.offline"})
        else:
            log.debug("fetching version from github", extra={"parent": "metadata"})
            metadata = json.loads(http_get(self.LATEST_RELEASE_METADTA).decode())
            remote_version = metadata["tag_name"]
            log.debug(f"raw version -> {remote_version}", extra={"parent": "metadata.online"})

        xm = VERSION_REGEX.match(local_version)
        x = (*xm.groups()[:3], xm.groups()[4])

        ym = VERSION_REGEX.match(remote_version)
        y = (*ym.groups()[:3], ym.groups()[4])

        local = "{}".format(".".join(x))
        log.debug(f"final local  = v{local}", extra={"parent": "metadata"})
        remote = "{}".format(".".join(y))
        log.debug(f"final remote = v{remote}", extra={"parent": "metadata"})
        return local, remote

    # def _display_pre_message(self, version: str) -> None:
    #     pass

    def _ensure_directories(self) -> None:
        self._cs_tools_cfg_dir.mkdir(parents=True, exist_ok=True)
        self._sys_exe_dir.mkdir(parents=True, exist_ok=True)

    def _install(self, version: str) -> int:
        with self.make_env(version) as env:

            if not self._setup:
                self._install_cs_tools(env)

            self._symlink_exe(env)
            self._set_path(env)

        return 0

    @contextmanager
    def make_env(self, version: str) -> VirtualEnvironment:
        if self._setup:
            yield VirtualEnvironment(self.venv_dir)
            return

        env_path_saved = self.venv_dir.with_suffix(".save")

        if self.venv_dir.exists():
            log.info("Saving existing environment.", extra={"parent": "install"})

            if env_path_saved.exists():
                shutil.rmtree(env_path_saved)

            shutil.move(self.venv_dir, env_path_saved)

        try:
            log.info("Creating environment.", extra={"parent": "install"})
            yield VirtualEnvironment.make(self.venv_dir)

        except Exception as e:
            if self.venv_dir.exists():
                log.warning("An error occurred. Removing partial environment.", extra={"parent": "install"})
                shutil.rmtree(self.venv_dir)

            if env_path_saved.exists():
                log.info("Restoring previously saved environment.", extra={"parent": "install"})
                shutil.move(env_path_saved, self.venv_dir)

            raise e

        if env_path_saved.exists():
            shutil.rmtree(env_path_saved, ignore_errors=True)

    def _install_cs_tools(self, env: VirtualEnvironment) -> None:
        if not self._offline_install:
            # fetch latest version from github
            # do some notifying that user is installing/upgrading their tools
            #
            raise NotImplementedError("coming soon...")
            return

        # poetry generates a list of packages which are required for cs_tools successful
        # installation, but not cs_tools itself (since poetry itself handles that bit).
        # take a 2-step process of installing all the dependencies, and then install
        # the cs_tools package.
        common = [
            # fmt: off
            "--find-links", PKGS.as_posix(),
            "--ignore-installed",
            "--no-index",
            "--no-deps"
            # fmt: on
        ]
        log.info("Installing requirements via pip.", extra={"parent": "install"})
        cp = env.pip("install", "-r", (PKGS / "requirements.txt").as_posix(), *common)
        log.debug(cp.stdout.decode(), extra={"parent": "install.pip"})

        log.info("Installing cs_tools via pip.", extra={"parent": "install"})
        cp = env.pip("install", "cs_tools", *common)
        log.debug(cp.stdout.decode(), extra={"parent": "install.pip"})

    def _symlink_exe(self, env):
        for script in entrypoints_from_whl(next(PKGS.glob("cs_tools*.whl"))):
            if WINDOWS:
                script += ".exe"

            source_script = env.bin_dir.joinpath(script)
            target_script = self._sys_exe_dir.joinpath(script)

            try:
                target_script.unlink()
            except FileNotFoundError:
                pass

            log.info(f"Attempting to symlink: '{target_script}' -> '{source_script}'", extra={"parent": "install"})

            try:
                target_script.symlink_to(source_script)
            except OSError:
                # This can happen if the user does not have the correct permissions
                # on Windows
                shutil.copy(source_script, target_script)

    def _set_path(self, env: VirtualEnvironment) -> None:
        if "fish" in SHELL:
            self._add_to_fish_path(str(env.bin_dir))
            return

        if WINDOWS:
            self._add_to_windows_path(str(env.bin_dir))
            return

        # Updating any profile we can on UNIX systems
        addition = (
            # fmt: off
            f"\n# absolute path to ThoughtSpot's CS Tools"
            # append to PATH (instead of prepend) in case of global python environment requiring common packages
            f'\nexport PATH="$PATH:{env.bin_dir}"'
            # You are dealing with an environment where Python thinks you are restricted to ASCII data.
            # https://click.palletsprojects.com/en/8.1.x/unicode-support/
            f"\nexport LC_ALL=en_US.utf-8"
            f"\nexport LANG=en_US.utf-8"
            f"\n"
            # fmt: on
        )

        for profile in self._get_unix_profiles():
            if not profile.exists():
                continue

            if addition not in profile.read_text():
                log.info(f"Adding {env.bin_dir} to {profile}")
                with profile.open(mode="a") as f:
                    f.write(addition)

    def _get_windows_path_var(self) -> Optional[str]:
        import winreg

        log.debug("attempting to get windows PATH variable")
        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as root:
            with winreg.OpenKey(root, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                path, _ = winreg.QueryValueEx(key, "PATH")
                return path

    def _set_windows_path_var(self, value: str) -> None:
        import ctypes
        import winreg

        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as root:
            with winreg.OpenKey(root, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, value)

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

    def _add_to_windows_path(self, value: str) -> None:
        try:
            current_path = self._get_windows_path_var()
        except OSError:
            current_path = None

        if current_path is None:
            log.warning("Unable to get the PATH value. It will not be updated.")
            return

        if value in current_path:
            log.warning(f"PATH already contains '{value}' and thus was not modified.")
            return

        log.info(f"Adding {value} to %PATH%")
        self._set_windows_path_var(f"{current_path};{value}")

    def _add_to_fish_path(self, value: str) -> None:
        current_path = os.environ.get("PATH", None)

        if current_path is None:
            log.warning("Unable to get the PATH value. It will not be updated.")
            return

        if value in current_path:
            log.warning(f"PATH already contains '{value}' and thus was not modified.")
            return

        user_paths = sp.check_output(["fish", "-c", "echo $fish_user_paths"]).decode("utf-8")

        if value not in user_paths:
            log.info(f"Adding {value} to $fish_user_paths")
            cmd = f"set -U fish_user_paths {value} $fish_user_paths"
            sp.check_output(["fish", "-c", f"{cmd}"])

    def _get_unix_profiles(self) -> None:
        profiles = [HOME.joinpath(".profile")]

        if "zsh" in SHELL:
            zdotdir = Path(os.getenv("ZDOTDIR", HOME))
            profiles.append(zdotdir.joinpath(".zprofile"))
            profiles.append(zdotdir.joinpath(".zshrc"))

        # .bash_profile is for login shells
        # .bashrc is for interactive shells
        for profile in ['.bash_profile', '.bashrc']:
            bash_profile = HOME.joinpath(profile)

            if bash_profile.exists():
                profiles.append(bash_profile)

        return profiles

    def _display_post_message(self, version: str) -> None:
        if WINDOWS:
            return self._display_post_message_windows(version)

        if SHELL == "fish":
            return self._display_post_message_fish(version)

        return self._display_post_message_unix(version)

    def _display_post_message_windows(self, version: str) -> None:
        path = self._get_windows_path_var()
        path_s = "\n>> ".join(path.split(";"))
        log.debug(f"$PATH\n>> {path_s}")
        message = POST_MESSAGE_NOT_IN_PATH

        # if path and str(self._sys_exe_dir) in path:
        if path and "cs_tools" in path:
            message = POST_MESSAGE

        log.note(
            message.format(
                version=version,
                sys_exe_dir=self._sys_exe_dir,
                executable=self._sys_exe_dir.joinpath("cs_tools.exe"),
                configure_message="""""",
                green="\033[0;32m",
                note="\033[1;34m",
                reset="\033[0m",
            )
        )

    def _display_post_message_fish(self, version: str) -> None:
        fish_user_paths = sp.check_output(["fish", "-c", "echo $fish_user_paths"]).decode()
        message = POST_MESSAGE_NOT_IN_PATH

        # if fish_user_paths and str(self._sys_exe_dir) in fish_user_paths:
        if fish_user_paths and "cs_tools" in fish_user_paths:
            message = POST_MESSAGE

        log.note(
            message.format(
                version=version,
                sys_exe_dir=self._sys_exe_dir,
                executable=self._sys_exe_dir.joinpath("cs_tools"),
                configure_message=POST_MESSAGE_CONFIGURE_FISH.format(
                    sys_exe_dir=self._sys_exe_dir,
                    green="\033[0;32m",
                    note="\033[1;34m",
                    reset="\033[0m",
                ),
                green="\033[0;32m",
                note="\033[1;34m",
                reset="\033[0m",
            )
        )

    def _display_post_message_unix(self, version: str) -> None:
        paths = os.getenv("PATH", "").split(":")
        message = POST_MESSAGE_NOT_IN_PATH

        # if paths and str(self._sys_exe_dir) in paths:
        if paths and "cs_tools" in paths:
            message = POST_MESSAGE

        log.note(
            message.format(
                version=version,
                sys_exe_dir=self._sys_exe_dir,
                executable=self._sys_exe_dir.joinpath("cs_tools"),
                configure_message=POST_MESSAGE_CONFIGURE_UNIX.format(
                    sys_exe_dir=self._sys_exe_dir,
                    green="\033[0;32m",
                    note="\033[1;34m",
                    yellow="\033[1;33m",
                ),
                green="\033[0;32m",
                note="\033[1;34m",
                reset="\033[0m",
            )
        )
