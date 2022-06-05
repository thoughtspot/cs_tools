from urllib.request import Request, urlopen
from pathlib import Path
import subprocess as sp
import tempfile
import sys

from _errors import CSToolsInstallationError
from _const import WINDOWS


class VirtualEnvironment:
    def __init__(self, path: Path) -> None:
        self._path = path

        # str() is required for compatibility with subprocess run on <= py3.7 on Windows
        self._python = str(
            self._path.joinpath("Scripts/python.exe" if WINDOWS else "bin/python")
        )

    @property
    def path(self):
        return self._path

    @classmethod
    def make(cls, target: Path) -> "VirtualEnvironment":
        try:
            import venv

            builder = venv.EnvBuilder(clear=True, with_pip=True, symlinks=False)
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
            raise CSToolsInstallationError(return_code=cp.returncode, log=cp.stdout.decode())

        return cp

    def python(self, *args, **kwargs) -> sp.CompletedProcess:
        return self.run(self._python, *args, **kwargs)

    def pip(self, *args, **kwargs) -> sp.CompletedProcess:
        return self.python("-m", "pip", "--isolated", *args, **kwargs)
