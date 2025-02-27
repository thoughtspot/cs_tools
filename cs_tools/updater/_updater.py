# /// script
# requires-python = ">= 3.9"
# dependencies = []
# ///
from __future__ import annotations

from typing import Union
import contextlib
import json
import logging
import os
import pathlib
import platform
import re
import shutil
import site
import subprocess as sp
import textwrap
import types
import venv

_LOG = logging.getLogger(__name__)
logging.getLogger("venv").setLevel(logging.ERROR)


class CSToolsVenv(venv.EnvBuilder):
    """
    Represents the managed CS Tools virtual environment.

    You do not need to have the venv activated in order to operate on it.
    """

    VENV_NAME = ".cs_tools"
    """Default name of the VirtualEnvironment."""

    TYPICAL_BUILD_DEPENDENCIES = ("wheel >= 0.45", "setuptools >= 75", "hatch", "maturin")
    """uv and pip do not discover these automatically."""

    def __init__(
        self,
        base_dir: pathlib.Path,
        *,
        offline_index: pathlib.Path | None = None,
        proxy: str | None = None,
        register_venv_path: bool = False,
        **venv_options,
    ):
        # MANDATORY OVERRIDES
        venv_options["with_pip"] = True

        super().__init__(**venv_options)
        self.base_dir = base_dir
        self.offline_index = None if offline_index is None else pathlib.Path(offline_index)
        self.proxy = proxy
        self.register_venv_path = register_venv_path

        # REDUNDANT, BUT NECESSARY IF WE'RE INSTANTIATING DIRECTLY.
        self.ctx = super().ensure_directories(self.base_dir / CSToolsVenv.VENV_NAME)

    def __str__(self) -> str:
        return f"<CSToolsVenv @ {self.base_dir} has_internet_access={self.has_internet_access}>"

    @property
    def python(self) -> pathlib.Path:
        """Get the venv python executable."""
        return pathlib.Path(self.ctx.env_exe)

    @property
    def has_internet_access(self) -> bool:
        """Determine if the venv can request packages from the internet."""
        return self.offline_index is None

    @property
    def path_manipulator(self) -> PATHManipulator:
        """Fetch the path manipulator."""
        return PATHManipulator.determine(venv=self)

    def subdir(self, stem: str) -> pathlib.Path:
        """Get a subdirectory of the CS Tools environment."""
        return self.base_dir / stem

    def run(
        self, *command: str, raise_if_stderr: bool = True, hush_logging: bool = False, **popen_options
    ) -> sp.CompletedProcess:
        """Run a subprocess command and stream its output."""
        STREAMING_OPTIONS = {
            "stdout": sp.PIPE,
            "stderr": sp.STDOUT,
            "text": True,
            "bufsize": 1,
            "universal_newlines": True,
        }

        if self.proxy is not None:
            popen_options.setdefault("env", {})
            popen_options["env"]["ALL_PROXY"] = self.proxy

        stdout_buffer: list[str] = []
        stderr_buffer: list[str] = []

        with sp.Popen(command, **popen_options | STREAMING_OPTIONS) as proc:
            assert proc.stdout is not None, "Something went seriously wrong if proc.stdout isn't set."

            for line in proc.stdout:
                if line.startswith("error") or line.startswith("warning"):
                    log_level_name = "ERROR" if line.lower().startswith("error") else "WARNING"
                    line = line.replace(f"{log_level_name.lower()}: ", "")
                    stderr_buffer.append(line)
                else:
                    log_level_name = "DEBUG" if hush_logging else "INFO"
                    stdout_buffer.append(line)

                if not line.strip():
                    continue

                try:
                    _LOG.log(level=logging.getLevelName(log_level_name), msg=line.strip())
                except TypeError:
                    _LOG.critical(f"FAILED TO CONVERT LOG LEVEL: '{log_level_name}' on line\n{line.strip()}\n\n")
                    _LOG.log(level=10, msg=line.strip())

        if raise_if_stderr and proc.returncode != 0:
            command_as_string = " ".join(command)
            _LOG.debug(f"Command:\n{command_as_string}")
            _LOG.debug(f"StandardOut:\n{json.dumps(stdout_buffer, indent=2)}")
            _LOG.debug(f"StandardErr:\n{json.dumps(stderr_buffer, indent=2)}")
            raise RuntimeError(f"Failed with exit code: {proc.returncode}\n\nRAN COMMAND BELOW\n{command_as_string}")

        output_as_bytes = "\n".join(stdout_buffer).encode()
        errors_as_bytes = "\n".join(stderr_buffer).encode()

        return sp.CompletedProcess(proc.args, proc.returncode, stdout=output_as_bytes, stderr=errors_as_bytes)

    @classmethod
    def default_base_path(cls) -> pathlib.Path:
        """Resolve to a User configuration-supported virtual environment directory."""
        DEFAULT_LOCATIONS = {
            "Windows": os.environ.get("APPDATA", "~"),
            "Darwin": "~/Library/Application Support",
            "Linux": os.environ.get("XDG_CONFIG_HOME", "~/.config"),
        }

        this_platform = platform.system()

        if this_platform not in DEFAULT_LOCATIONS:
            raise RuntimeError(
                f"Could not recognize the platform '{this_platform}'. Do you need a managed virtual enivonment or "
                f"would you be better off installing CS Tools manually with pip or uv?"
            )

        cs_tools_base_path = pathlib.Path(DEFAULT_LOCATIONS[this_platform]).expanduser() / "cs_tools"
        cs_tools_venv_path = cs_tools_base_path / CSToolsVenv.VENV_NAME

        # BPO-45337 - handle Micrsoft Store downloads
        #   @steve.dower
        #     We *could* limit this to when it's under AppData, but I think limiting it to Windows is enough.
        #     If the realpath generated a different path, we should warn the caller.
        #     If someone is looking at the output they'll get an important hint.
        #
        #   Further reading: https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-behind-the-scenes
        #
        if this_platform == "Windows":
            ctx = venv.EnvBuilder().ensure_directories(cs_tools_venv_path)

            if cs_tools_venv_path.resolve() != pathlib.Path(ctx.env_dir).resolve():
                _LOG.debug(
                    f"Actual environment location may have moved due to redirects, links or junctions."
                    f"\n  Requested location: '{cs_tools_venv_path}'"
                    f"\n  Actual location:    '{ctx.env_dir}'",
                )
                cs_tools_base_path = pathlib.Path(ctx.env_dir)

        return cs_tools_base_path.resolve()

    @classmethod
    def make(
        cls,
        venv_directory: Union[str, pathlib.Path, None] = None,
        *,
        reset_venv: bool = False,
        **venv_options,
    ) -> CSToolsVenv:
        """Create a managed virutal environment at the given directory."""
        venv_directory = cls.default_base_path() if venv_directory is None else pathlib.Path(venv_directory)

        assert venv_directory.is_dir(), "venv_directory must be a valid directory!"

        if reset_venv:
            _LOG.debug(f"Resetting CS Tools virtual environment at {venv_directory / CSToolsVenv.VENV_NAME}")
            shutil.rmtree(venv_directory / CSToolsVenv.VENV_NAME, ignore_errors=True)

        env = cls(base_dir=venv_directory, **venv_options)

        if not env.python.exists():
            _LOG.debug(f"Creating CS Tools virtual environment at {venv_directory}")
            env.create(env_dir=venv_directory / CSToolsVenv.VENV_NAME)

        return env

    # STEP 1. in EnvBuilder().create(env_dir)
    # https://docs.python.org/3/library/venv.html#venv.EnvBuilder.ensure_directories
    def ensure_directories(self, env_dir: pathlib.Path) -> types.SimpleNamespace:  # type: ignore[override]
        """Creates the env directory and necessary subdirectories."""
        self.ctx = ctx = super().ensure_directories(env_dir=env_dir)

        # INJECT OUR OWN AT THE ROOT OF THE CS TOOLS ENVIRONMENT AS WELL.
        _LOG.debug(f"Setting up CS Tools accessory directories at {self.ctx.env_dir}")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.subdir(".cache").mkdir(exist_ok=True)
        self.subdir(".logs").mkdir(exist_ok=True)
        self.subdir(".tmp").mkdir(exist_ok=True)

        return ctx

    # STEP 5. in EnvBuilder().create(env_dir)  [FINAL]
    # https://docs.python.org/3/library/venv.html#venv.EnvBuilder.post_setup
    def post_setup(self, _ctx: types.SimpleNamespace) -> None:
        """Called once the environment is finalized."""
        # INSTALL uv, WHO WILL MANAGE OUR DEPENDENCIES.
        self.install("uv", "--disable-pip-version-check", with_pip=True)

        # ADD OUR EXECUTABLE TO THE PATH VARIABLE.
        if self.register_venv_path:
            self.path_manipulator.install()

    def install(
        self,
        package_spec: str,
        *extra_arguments: str,
        with_pip: bool = False,
        editable: bool = False,
        **extra_options,
    ) -> None:
        """Install a package using uv."""
        extra_arguments = list(extra_arguments)  # type: ignore[assignment]
        assert isinstance(extra_arguments, list), "Extra arguments have been reassigned for typing purposes."

        TRUSTED_INSTALL_LOCATIONS = (
            "files.pythonhosted.org",
            "pypi.org",
            "pypi.python.org",
            "github.com",
            "codeload.github.com",
        )

        if self.has_internet_access:
            for location in TRUSTED_INSTALL_LOCATIONS:
                option_name = "--trusted-host" if with_pip else "--allow-insecure-host"
                extra_arguments.extend([option_name, location])
        else:
            # extra_arguments.extend(["--offline"]) if not with_pip else None
            extra_arguments.extend(["--no-index", "--find-links", self.offline_index.as_posix()])

        _LOG.debug(f"Attempting to install '{package_spec}' into the virtual environment.")

        installer = ("pip",) if with_pip else ("uv", "pip")

        # ALL OF THESE ARE VALID FOR package_spec
        #
        # eg. pip install .. git+https://github.com/thoughtspot/cs_tools/cs_tools.git
        # eg. pip install .. "cs_tools[cli] @ ./cs_tools"
        # eg. pip install .. --editable "cs_tools[cli] @ ./cs_tools"
        package_spec = ["--editable", package_spec] if editable else [package_spec]

        self.run(self.python.as_posix(), "-m", *installer, "install", *package_spec, *extra_arguments, **extra_options)

    def make_offline_distribution(
        self,
        output_dir: Union[str, pathlib.Path],
        *,
        platform: str | None = None,
        python_version: str | None = None,
    ) -> None:
        """
        Create an offline distribution of this CS Tools environment.

        Q. How can I find my platform?
        >>> python -c "from pip._vendor.packaging.tags import platform_tags; print(next(iter(platform_tags())))"

        Q. How can I find my python version?
        >>> python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        """
        _LOG.debug(f"Creating offline distribution in {output_dir}")
        output_dir = pathlib.Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # ENSURE WE HAVE THE BUILD DEPENDENCIES VENDORED AS WELL.
        self.install(*CSToolsVenv.TYPICAL_BUILD_DEPENDENCIES)

        # GET LIST OF INSTALLED PACKAGES
        _LOG.debug("Freezing CS Tools venv > requirements-freeze.txt")
        reqs_txt = output_dir.joinpath("requirements-freeze.txt")
        rc = self.run(self.python.as_posix(), "-m", "uv", "pip", "freeze", "--exclude-editable")
        reqs_txt.write_bytes(
            b"\n".join(
                line
                for line in rc.stdout.split(b"\n\n")
                # IGNORE THE FIRST LINE WHEN WE ARE EXECUTING `uv` FROM OUTSIDE OF THE VIRTUAL ENVIRONMENT, WHICH
                # GENERATES A HEADER ... Using Python 3.12.3 environment at: <PATH>
                if not line.startswith(b"Using Python ")
            )
        )

        # fmt: off
        # NOW USE PIP (NOT UV) TO DOWNLOAD THE PACKAGES
        command = [
            self.python.as_posix(), "-m", "pip", "download",
            "--requirement", reqs_txt.as_posix(),
            "--dest", output_dir.as_posix(),
            "--no-deps", "--disable-pip-version-check",
        ]
        # fmt: on

        if platform:
            command.extend(["--platform", platform])

        if python_version:
            command.extend(["--python-version", python_version])

        # DOWNLOAD ALL THE PACKAGES
        self.run(*command)


cs_tools_venv = CSToolsVenv(base_dir=CSToolsVenv.default_base_path())


class PATHManipulator:
    """An interface to modifying the PATH environment variable."""

    def __init__(self, venv: CSToolsVenv) -> None:
        self.venv = venv

    @property
    def executable_directory(self) -> pathlib.Path:
        """The directory of the python executable."""
        return self.venv.python.parent

    @classmethod
    def determine(cls, venv: CSToolsVenv) -> PATHManipulator:
        """Determine the correct PATHManipulator for the current platform."""

        if "fish" in os.environ.get("SHELL", ""):
            return FishPath(venv=venv)

        if platform.system() == "Windows":
            return WindowsPath(venv=venv)

        return UnixPath(venv=venv)

    def install(self) -> None:
        """Inject the executable directory into the PATH variable longterm."""
        raise NotImplementedError

    def uninstall(self) -> None:
        """Remove the executable directory from the PATH variable."""
        raise NotImplementedError


class FishPath(PATHManipulator):
    """
    fish's PATH is managed via the fish CLI.

    Further Reading:
       https://fishshell.com/docs/current/tutorial.html#path
    """

    def install(self) -> None:
        """Inject the executable directory into the PATH variable longterm."""
        # THIS IS INDEMPOTENT, SO WE'RE FREE TO ADD WITHOUT CHCEKING.
        _LOG.info(f"Adding '{self.executable_directory}' to $fish_user_paths")
        sp.check_output(["fish_add_path", self.executable_directory.as_posix()])

    def uninstall(self) -> None:
        """Remove the executable directory from the PATH variable."""
        _LOG.info(f"Removing '{self.executable_directory}' from $fish_user_paths")
        sp.check_output(["set", "PATH", f"(string match -v {self.executable_directory.as_posix()} $PATH)"])


class WindowsPath(PATHManipulator):
    """
    Window's PATH is best managed with User ENVIRONMENT Variables.

    Further Reading:
      https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/windows-registry-advanced-users
    """

    SYSTEM_EXECUTABLE_DIRECTORY: pathlib.Path = pathlib.Path(site.getuserbase()) / "Scripts"
    """The directory of the system python executable."""

    @classmethod
    def BROADCAST_UPDATE(cls) -> None:
        """Tell other processes to update their ENVIRONMENT."""
        import ctypes

        HWND_BROADCAST = 0xFFFF
        """https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendnotifymessagea#parameters"""

        WM_SETTINGCHANGE = 0x1A
        """https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-settingchange"""

        SMTO_ABORTIFHUNG = 0x0002
        """https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagetimeouta"""

        result = ctypes.c_long()

        """https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagetimeoutw"""
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_SETTINGCHANGE,
            0,
            "Environment",
            SMTO_ABORTIFHUNG,
            5000,
            ctypes.byref(result),
        )

    @classmethod
    @contextlib.contextmanager
    def OPEN_REGISTRY_EDITOR(cls):
        """
        This is like opening regedit.exe to the following path.

        Computer
        └─ HKEY_CURRENT_USER
           └─ ENVIRONMENT
        """
        import winreg

        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as root:
            with winreg.OpenKey(root, "Environment", 0, winreg.KEY_ALL_ACCESS) as key:
                yield key

    @classmethod
    def symlink_paths(cls, target: pathlib.Path, original: pathlib.Path) -> None:
        """Attempt to symlink in Windows."""
        _LOG.warning("Could not access the USER %PATH% directly, falling back to building a junction.")

        try:
            _LOG.info(f"Attempting to symlink: '{target}' -> '{original}'")
            target.unlink(missing_ok=True)
            target.symlink_to(original)

        # THIS CAN HAPPEN IF THE USER DOES NOT HAVE THE CORRECT PERMISSIONS ON WINDOWS
        except OSError:
            _LOG.info("Symlink failed, bruteforce copying instead..")
            shutil.copy(original, target)

    def install(self) -> None:
        """Inject the executable directory into the PATH variable longterm."""
        import winreg

        with WindowsPath.OPEN_REGISTRY_EDITOR() as USR_ENV_VARS:
            PATH, _ = winreg.QueryValueEx(USR_ENV_VARS, "PATH")

            # COULDN'T GET PATH VARIABLE FROM REGISTRY, SO WE HAVE TO TRY TO BRUTEFORCE
            # THE PATH LINKING. FIRST TRY TO SYMLINK, THEN JUST COPY THE DAMN THING.
            if PATH is None:
                source = self.executable_directory
                target = WindowsPath.SYSTEM_EXECUTABLE_DIRECTORY
                WindowsPath.symlink_paths(target=target / "cs_tools.exe", original=source / "cs_tools.exe")
                WindowsPath.symlink_paths(target=target / "cstools.exe", original=source / "cstools.exe")
                return

            # APPEND TO THE PATH VARIABLE
            if self.executable_directory.as_posix() not in PATH:
                _LOG.info(f"Adding '{self.executable_directory}' to User %PATH%")
                PATH = f"{PATH};{self.executable_directory.as_posix()}"
                winreg.SetValueEx(USR_ENV_VARS, "PATH", 0, winreg.REG_EXPAND_SZ, PATH)

        WindowsPath.BROADCAST_UPDATE()

    def uninstall(self) -> None:
        """Remove the executable directory from the PATH variable."""
        import winreg

        with WindowsPath.OPEN_REGISTRY_EDITOR() as USR_ENV_VARS:
            PATH, _ = winreg.QueryValueEx(USR_ENV_VARS, "PATH")

            # COULDN'T GET THE PATH VARIABLE FROM REGISTRY
            if PATH is None:
                (WindowsPath.SYSTEM_EXECUTABLE_DIRECTORY / "cs_tools.exe").unlink(missing_ok=True)
                (WindowsPath.SYSTEM_EXECUTABLE_DIRECTORY / "cstools.exe").unlink(missing_ok=True)
                return

            _LOG.info(f"Removing '{self.executable_directory}' from User %PATH%")
            PATH = PATH.replace(f";{self.executable_directory.as_posix()}", "")
            winreg.SetValueEx(USR_ENV_VARS, "PATH", 0, winreg.REG_EXPAND_SZ, PATH)

        WindowsPath.BROADCAST_UPDATE()


class UnixPath(PATHManipulator):
    """Linux's PATH are canonically managed via $SHELL profiles."""

    HOME_DIRECTORY: pathlib.Path = pathlib.Path("~").expanduser().resolve()
    """The directory that $HOME resolves to."""

    @classmethod
    def AVAILABLE_SHELL_PROFILES(cls) -> list[pathlib.Path]:
        """Detect which $SHELL profiles currently exist on the system."""
        found_profiles = []

        # $SHELL RESOLVES TO Z SHELL.
        # .zprofile .. IS FOR LOGIN SHELLS
        # .zshrc ..... IS FOR INTERACTIVE SHELLS
        if "zsh" in os.environ.get("SHELL", ""):
            zdotdir = pathlib.Path(os.getenv("ZDOTDIR", UnixPath.HOME_DIRECTORY))

            for stem in (".zprofile", ".zshrc"):
                if (profile := zdotdir / stem).exists():
                    found_profiles.append(profile)

        # $SHELL RESOLVES TO BASH.
        # .bash_profile .. IS FOR LOGIN SHELLS
        # .bashrc ........ IS FOR INTERACTIVE SHELLS
        for stem in (".bash_profile", ".bashrc"):
            if (profile := UnixPath.HOME_DIRECTORY / stem).exists():
                found_profiles.append(profile)

        # ENSURE AT LEAST THE BASE $SHELL PROFILE EXISTS.
        if not found_profiles:
            base_profile = UnixPath.HOME_DIRECTORY / ".profile"
            base_profile.touch(exist_ok=True)
            found_profiles.append(base_profile)

        return found_profiles

    def generate_profile_snippet(self) -> str:
        """The snippet to inject into the profile."""

        # DEV NOTE: @boonhapus 2024/11/30
        # - Add our directory to the end of the PATH so we don't clobber other python-based exports.
        # - Previously we set LC_ALL and LANG, but PEP 538 and PEP 540 fixed this in Python >= 3.7 .

        # fmt: off
        snippet = textwrap.dedent(
            f"""
            # :: CS_TOOLS_START
            # The absolute path to ThoughtSpot's CS Tools"
            export PATH="$PATH:{self.executable_directory.as_posix()}"
            # :: CS_TOOLS_END
            """
        )
        # fmt: on

        return snippet

    def install(self) -> None:
        """Inject the executable directory into the PATH variable longterm."""
        snippet = self.generate_profile_snippet()

        for profile_path in UnixPath.AVAILABLE_SHELL_PROFILES():
            # DON'T WRITE TO PROFILES MULTIPLE TIMES
            if snippet in profile_path.read_text():
                continue

            _LOG.info(f"Adding the '{self.executable_directory}' PATH snippet to '{profile_path.resolve()}'")

            with profile_path.open(mode="a") as f:
                f.write(snippet)

    def uninstall(self) -> None:
        """Remove the executable directory from the PATH variable."""
        snippet = self.generate_profile_snippet()

        for profile_path in UnixPath.AVAILABLE_SHELL_PROFILES():
            # ONLY MODIFY PROFILES WHICH CONTAIN THE SNIPPET
            if snippet not in (contents := profile_path.read_text()):
                continue

            _LOG.info(f"Removing the '{self.executable_directory}' PATH snippet from '{profile_path.resolve()}'")

            cleaned = re.sub(
                # # :: CS_TOOLS_START ... acts like a boundary
                # [\S\s]+  .............. matches 1 or more of any non-whitespace or any whitespace character
                # # :: CS_TOOLS_START ... acts like a boundary
                pattern=r"(# :: CS_TOOLS_START[\S\s]+# :: CS_TOOLS_END)",
                repl="",
                string=contents,
                flags=re.MULTILINE,
            )

            with profile_path.open(mode="w") as f:
                f.write(cleaned)


if __name__ == "__main__":
    import sys

    from pip._vendor.packaging.tags import platform_tags

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)-8s | %(asctime)s | %(filename)s:%(lineno)d | %(message)s",
    )

    #
    # BASIC VENV TEST.
    #

    HERE_DIR = pathlib.Path(__file__).parent
    BASE_DIR = pathlib.Path()

    # SIMULATE USER INPUT.
    THIS_PLAT = next(iter(platform_tags()))
    THIS_VERS = f"{sys.version_info.major}.{sys.version_info.minor}"

    # FRESH-INSTALL OF A NEW VENV.
    env = CSToolsVenv.make(venv_directory=BASE_DIR / "mk-venv", reset_venv=True, register_venv_path=True)

    _LOG.info(f"CS TOOLS VENV INFO:\n========\n{env}\n========")

    # INSTALL A PACKAGE.
    env.install(f"cs_tools[cli] @ {HERE_DIR.parent.parent}")
    # or ... env.install("cs_tools[cli] @ https://github.com/thoughtspot/cs_tools/archive/v1.6.0.zip")

    # BUILD AN OFFLINE BINARY.
    _LOG.debug("Ensuring the necessary build system packages are installed for 'source distributed' requirements.")
    env.install(f"cs_tools[offline] @ {HERE_DIR.parent.parent}")
    env.make_offline_distribution(output_dir=BASE_DIR / "offline-dist", platform=THIS_PLAT, python_version=THIS_VERS)

    # RE-CREATE THE VENV IN OFFLINE MODE.
    env = CSToolsVenv.make(
        venv_directory=BASE_DIR / "mk-venv", reset_venv=True, offline_index=BASE_DIR / "offline-dist"
    )

    _LOG.info(f"CS TOOLS VENV INFO:\n========\n{env}\n========")

    # ATTEMPT THE SAME PACKAGE INSTALL, WITHOUT INTERNET ACCESS.
    env.install(f"cs_tools[cli] @ {HERE_DIR.parent.parent}")
