from urllib.request import Request, urlopen
from pathlib import Path
import subprocess as sp
import tempfile
import sys
import os

from _errors import CSToolsInstallationError
from _const import WINDOWS


class VirtualEnvironment:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    @property
    def shell(self):
        shell = None

        if os.name == "posix":
            shell = os.environ.get("SHELL")
        elif os.name == "nt":
            shell = os.environ.get("COMSPEC")

        if not shell:
            raise RuntimeError("Unable to detect the current shell.")

        return Path(shell)

    @property
    def bin_dir(self) -> Path:
        dir_ = "Scripts" if WINDOWS else "bin"
        return self.path / dir_

    @property
    def exe(self) -> Path:
        py_exe = "python.exe" if WINDOWS else "python"
        return self.bin_dir / py_exe

    @classmethod
    def make(cls, target: Path) -> "VirtualEnvironment":
        try:
            import venv

            builder = venv.EnvBuilder(clear=True, with_pip=True, symlinks=not WINDOWS)
            builder.ensure_directories(target)
            builder.create(target)
        except ImportError:
            # fallback to using virtualenv package if venv is not available, eg: ubuntu
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            virtualenv_bootstrap_url = (
                f"https://bootstrap.pypa.io/virtualenv/{python_version}/virtualenv.pyz"
            )

            with tempfile.TemporaryDirectory(prefix="cstools-installer") as temp_dir:
                virtualenv_pyz = Path(temp_dir) / "virtualenv.pyz"
                request = Request(
                    virtualenv_bootstrap_url, headers={"User-Agent": "CS Tools"}
                )
                virtualenv_pyz.write_bytes(urlopen(request).read())
                cls.run(
                    sys.executable, virtualenv_pyz, "--clear", "--always-copy", target
                )

        # We add a special file so that Poetry can detect its own virtual environment
        # just in case
        target.joinpath("poetry_env").touch()

        env = cls(target)

        # we do this here to ensure that outdated system default pip does not trigger
        # older bugs
        env.pip("install", "--disable-pip-version-check", "--upgrade", "pip")
        return env

    @staticmethod
    def run(*args, **kwargs) -> sp.CompletedProcess:
        cp = sp.run(args, stdout=sp.PIPE, stderr=sp.STDOUT, **kwargs)

        if cp.returncode != 0:
            raise CSToolsInstallationError(
                return_code=cp.returncode,
                log=cp.stdout.decode()
            )

        return cp

    def python(self, *args, **kwargs) -> sp.CompletedProcess:
        # str() is required for compatibility with subprocess run on <= py3.7 on Windows
        return self.run(str(self.exe), *args, **kwargs)

    def pip(self, *args, **kwargs) -> sp.CompletedProcess:
        return self.python("-m", "pip", "--isolated", *args, **kwargs)

    def activate(self) -> int:
        if self.shell.stem in ("powershell", "pwsh"):
            suffix = ".ps1"
        elif self.shell.stem == "cmd":
            suffix = ".bat"
        else:
            suffix = ""

        activate_path = f'{self.bin_dir}/activate{suffix}'

        # mypy requires using sys.platform instead of WINDOWS constant
        # in if statements to properly type check on Windows
        if sys.platform == "win32":
            if self.shell.stem in ("powershell", "pwsh"):
                args = ["-NoExit", "-File", str(activate_path)]
            else:
                # /K will execute the bat file and
                # keep the cmd process from terminating
                args = ["/K", str(activate_path)]

            print(self._path, *args)
            completed_proc = sp.run([self.shell.stem, *args], shell=True)
            return completed_proc.returncode

        # import shlex

        # terminal = Terminal()
        # with env.temp_environ():
        #     c = pexpect.spawn(
        #         self._path, ["-i"], dimensions=(terminal.height, terminal.width)
        #     )

        # if self._name == "zsh":
        #     c.setecho(False)

        # c.sendline(f"{self._get_source_command()} {shlex.quote(str(activate_path))}")

        # def resize(sig: Any, data: Any) -> None:
        #     terminal = Terminal()
        #     c.setwinsize(terminal.height, terminal.width)

        # signal.signal(signal.SIGWINCH, resize)

        # # Interact with the new shell.
        # c.interact(escape_character=None)
        # c.close()

        # sys.exit(c.exitstatus)

    def _get_source_command(self) -> str:
        if self.shell in ("fish", "csh", "tcsh"):
            return "source"
        return "."

