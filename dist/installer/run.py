"""
This script will install cs_tools and its dependencies.

It does, in order:
  - Creates a virtual environment using venv (or virtualenv zipapp) in the correct OS data dir which will be
      - `%APPDATA%\\pypoetry` on Windows
      -  ~/Library/Application Support/pypoetry on MacOS
      - `${XDG_DATA_HOME}/pypoetry` (or `~/.local/share/pypoetry` if it's not set) on UNIX systems
      - In `${POETRY_HOME}` if it's set.

  - Installs the latest or given version of Poetry inside this virtual environment.
  - Installs a `poetry` script in the Python user directory (or `${POETRY_HOME/bin}` if `POETRY_HOME` is set).
  - On failure, the error log is written to poetry-installer-error-*.log and any previously existing environment
    is restored.
"""
from contextlib import contextmanager
from typing import Tuple
from pathlib import Path
import subprocess as sp
import traceback
import tempfile
import argparse
import shutil
import json
import sys

from _virtual_env import VirtualEnvironment
from _terminal import Cursor, is_decorated
from _errors import CSToolsInstallationError
from _const import WINDOWS, PRE_MESSAGE, PKGS_DIR, VERSION_REGEX
from _util import app_dir, bin_dir, compare_versions, http_get


ReturnCode = int


class Installer:
    LATEST_RELEASE_METADTA = 'https://api.github.com/repos/thoughtspot/cs_tools/releases/latest'

    def __init__(
        self,
        offline_install: bool = True,
        reinstall: bool = False
    ):
        self._offline_install = offline_install
        self._reinstall = reinstall
        self._config_dir = Path(app_dir())
        self._bin_dir = bin_dir(self._config_dir)
        self._cursor = Cursor()

    # CORE METHODS

    def run(self) -> ReturnCode:
        self._write("")
        local, remote = self.get_versions()

        if remote is None:
            return 0

        if self._reinstall:
            pass
        elif compare_versions(local, remote) >= 0:
            self._write('You have the latest version of CS Tools already!\n')
            return 0

        self.display_pre_message()
        self.ensure_directories()

        try:
            self.install(remote)
        except sp.CalledProcessError as e:
            raise CSToolsInstallationError(return_code=e.returncode, log=e.output.decode())

        self._write("")
        # self.display_post_message(local)
        return 0

    def install(self, version: str) -> ReturnCode:
        """
        Installs CS Tools.
        """
        self._write("Installing {} ({})".format("CS Tools", version))

        with self.make_env(version) as env:
            self.install_cs_tools(version, env)
            # self.make_bin(version, env)
            self._install_comment(version, "Done")
            return 0

    # SUPPORTING METHODS

    def get_versions(self) -> Tuple[str, str]:
        self._write("Retrieving CS Tools metadata..")

        if (self._bin_dir / "activate").exists():
            exe = self._bin_dir / 'cs_tools.exe' if WINDOWS else self._bin_dir / 'cs_tools'
            cp = sp.run([exe.as_posix(), '--version'], stdout=sp.PIPE, stderr=sp.STDOUT)

            if cp.returncode != 0:
                raise CSToolsInstallationError(return_code=cp.returncode, log=cp.stdout.decode())

            _, _, local_version = cp.stdout.decode().partition('(')
        else:
            local_version = "0.0.0"

        if self._offline_install:
            fp = next((Path(__file__).parent.parent / 'pkgs').glob('cs_tools*.whl'))
            _, remote_version, *_ = fp.name.split('-')
        else:
            metadata = json.loads(http_get(self.LATEST_RELEASE_METADTA).decode())
            remote_version = metadata["tag_name"]

        x = VERSION_REGEX.match(local_version).groups()[:3]
        y = VERSION_REGEX.match(remote_version).groups()[:3]
        self._cursor.move_up()
        self._cursor.clear_line()
        return 'v{}'.format('.'.join(x)), 'v{}'.format('.'.join(y))

    def ensure_directories(self) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._bin_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def make_env(self, version: str) -> VirtualEnvironment:
        env_path = self._config_dir.joinpath(".cs_tools")
        env_path_saved = env_path.with_suffix(".save")

        if env_path.exists():
            self._install_comment(version, "Saving existing environment")
            if env_path_saved.exists():
                shutil.rmtree(env_path_saved)
            shutil.move(env_path, env_path_saved)

        try:
            self._install_comment(version, "Creating environment")
            yield VirtualEnvironment.make(env_path)
        except Exception as e:
            if env_path.exists():
                self._install_comment(
                    version, "An error occurred. Removing partial environment."
                )
                shutil.rmtree(env_path)

            if env_path_saved.exists():
                self._install_comment(version, "Restoring previously saved environment.")
                shutil.move(env_path_saved, env_path)

            raise e
        else:
            if env_path_saved.exists():
                shutil.rmtree(env_path_saved, ignore_errors=True)

    def install_cs_tools(self, version: str, env: VirtualEnvironment) -> None:
        self._install_comment(version, "Installing CS Tools")

        if self._offline_install:
            specification = f"cs_tools=={version}"
            # reqs = (Path(PKGS_DIR) / 'requirements.txt').as_posix()
            args = ["--find-links", PKGS_DIR, "--no-index"]#, "-r", reqs]
        else:
            ...
            specification = f"cs_tools=={version}"
            args = []

        env.pip("install", specification, *args)

    # CLI INTERACTION

    def _write(self, line) -> None:
        sys.stdout.write(line + "\n")

    def _overwrite(self, line) -> None:
        if not is_decorated():
            return self._write(line)

        self._cursor.move_up()
        self._cursor.clear_line()
        self._write(line)

    def _install_comment(self, version: str, message: str) -> None:
        self._overwrite("Installing {} ({}): {}".format("CS Tools", version, message))

    def display_pre_message(self) -> None:
        kwargs = {"cs_tools": "CS Tools", "cs_tools_home_bin": self._bin_dir}
        self._write(PRE_MESSAGE.format(**kwargs))

    # def display_post_message(self, version) -> None:
    #     if WINDOWS:
    #         return self.display_post_message_windows(version)

    #     if SHELL == "fish":
    #         return self.display_post_message_fish(version)

    #     return self.display_post_message_unix(version)


#
#
#


def main() -> ReturnCode:
    parser = argparse.ArgumentParser(description="Installs the latest version of cs_tools")
    parser.add_argument(
        "-f",
        "--fetch-remote",
        help="fetching the latest version of cs_tools available online",
        dest="fetch_remote",
        action="store_true",
        default=False
    )
    parser.add_argument(
        "-r",
        "--reinstall",
        help="install on top of existing version",
        dest="reinstall",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()

    installer = Installer(
        offline_install=not args.fetch_remote,
        reinstall=args.reinstall,
    )

    try:
        return installer.run()
    except CSToolsInstallationError as e:
        installer._write("[ERROR] CSTools installation failed.")

        if e.log is not None:
            _, path = tempfile.mkstemp(suffix=".log", prefix="cs_tools-installer-error-", dir=str(Path.cwd()), text=True)
            installer._write(f"[ERROR] See {path} for error logs.")
            tb = ''.join(traceback.format_tb(e.__traceback__))
            Path(path).write_text(f"{e.log}\n\nTraceback:\n{tb}")

        return e.return_code


if __name__ == "__main__":
    raise SystemExit(main())
