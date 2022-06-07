from contextlib import contextmanager
import pathlib
import shutil
import os

from _virtual_env import VirtualEnvironment
from _util import app_dir


class Installer:

    def __init__(
        self,
        offline_install: bool = True,
        reinstall: bool = False
    ):
        self._offline_install = offline_install
        self._reinstall = reinstall
        self._cs_tools_cfg_dir = pathlib.Path(app_dir())

        # todo
        self._write = lambda *args: print(*args)
        self._install_comment = lambda v, *args: print(f'({v}):', *args)

    @property
    def venv_path(self) -> str:
        return self._cs_tools_cfg_dir / ".cs_tools"

    @contextmanager
    def make_env(self, version: str) -> VirtualEnvironment:
        env_path_saved = self.env_path.with_suffix(".save")

        if self.venv_path.exists():
            self._install_comment(version, "Saving existing environment")
            if env_path_saved.exists():
                shutil.rmtree(env_path_saved)
            shutil.move(self.venv_path, env_path_saved)

        try:
            self._install_comment(version, "Creating environment")
            yield VirtualEnvironment.make(self.venv_path)
        except Exception as e:
            if self.venv_path.exists():
                self._install_comment(
                    version, "An error occurred. Removing partial environment."
                )
                shutil.rmtree(self.venv_path)

            if env_path_saved.exists():
                self._install_comment(version, "Restoring previously saved environment.")
                shutil.move(env_path_saved, self.venv_path)

            raise e
        else:
            if env_path_saved.exists():
                shutil.rmtree(env_path_saved, ignore_errors=True)

    def run(self) -> int:
        self._write("")
        # local, remote = self.get_versions()
        local, remote = "0.0.0", "1.3.2"
        raise

        # if remote is None:
        #     return 0

        # if self._reinstall:
        #     pass
        # elif compare_versions(local, remote) >= 0:
        #     self._write('You have the latest version of CS Tools already!\n')
        #     return 0

        # self.display_pre_message()
        self.ensure_directories()

        try:
            self.install(remote)
        except sp.CalledProcessError as e:
            raise CSToolsInstallationError(return_code=e.returncode, log=e.output.decode())

        self._write("")
        # self.display_post_message(local)
        return 0

    def install(self, version: str) -> int:
        self._write("Installing {} ({})".format("CS Tools", version))

        with self.make_env(version) as env:
            self.install_cs_tools(version, env)
            self._install_comment(version, "Done")
            return 0

    def activate(self) -> int:
        env = VirtualEnvironment(self.venv_path)
        return env.activate()

