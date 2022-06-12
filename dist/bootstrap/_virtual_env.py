from urllib.request import Request, urlopen
from pathlib import Path
import subprocess as sp
import tempfile
import sys

from _errors import CSToolsActivatorError
from _const import WINDOWS


class VirtualEnvironment:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

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
            virtualenv_bootstrap_url = f"https://bootstrap.pypa.io/virtualenv/{python_version}/virtualenv.pyz"

            with tempfile.TemporaryDirectory(prefix="cstools-installer") as temp_dir:
                virtualenv_pyz = Path(temp_dir) / "virtualenv.pyz"
                request = Request(virtualenv_bootstrap_url, headers={"User-Agent": "CS Tools"})
                virtualenv_pyz.write_bytes(urlopen(request).read())
                cls.run(sys.executable, virtualenv_pyz, "--clear", "--always-copy", target)

        env = cls(target)

        # we do this here to ensure that outdated system default pip does not trigger
        # older bugs
        env.pip("install", "--disable-pip-version-check", "--upgrade", "pip")
        return env

    @staticmethod
    def run(*args, raise_on_failure: bool = True, **kwargs) -> sp.CompletedProcess:
        cp = sp.run(args, stdout=sp.PIPE, stderr=sp.STDOUT, **kwargs)

        if raise_on_failure and cp.returncode != 0:
            raise CSToolsActivatorError(return_code=cp.returncode, log=cp.stdout.decode())

        return cp

    def python(self, *args, **kwargs) -> sp.CompletedProcess:
        # str() is required for compatibility with subprocess run on <= py3.7 on Windows
        return self.run(str(self.exe), *args, **kwargs)

    def pip(self, *args, **kwargs) -> sp.CompletedProcess:
        return self.python("-m", "pip", "--isolated", *args, **kwargs)
