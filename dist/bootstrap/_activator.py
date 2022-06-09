from contextlib import contextmanager
from typing import Tuple
import subprocess as sp
import shutil
import json

from _virtual_env import VirtualEnvironment
from _errors import CSToolsActivatorError
from _const import PKGS_DIR, VERSION_REGEX, WINDOWS
from _util import app_dir, bin_dir, compare_versions, http_get, entrypoints_from_whl


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
    """
    def __init__(self, offline_install: bool = True, reinstall: bool = False):
        self._offline_install = offline_install
        self._reinstall = reinstall
        self._cs_tools_cfg_dir = app_dir('cs_tools')
        self._executable_dir = bin_dir()

        # todo
        self._write = lambda *args: print(*args)
        self._install_comment = lambda v, *args: print(f'({v}):', *args)

    @property
    def venv_path(self) -> str:
        return self._cs_tools_cfg_dir.joinpath(".cs_tools")

    @contextmanager
    def make_env(self, version: str) -> VirtualEnvironment:
        env_path_saved = self.venv_path.with_suffix(".save")

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
                self._install_comment(version, "An error occurred. Removing partial environment.")
                shutil.rmtree(self.venv_path)

            if env_path_saved.exists():
                self._install_comment(version, "Restoring previously saved environment.")
                shutil.move(env_path_saved, self.venv_path)

            raise e
        else:
            if env_path_saved.exists():
                shutil.rmtree(env_path_saved, ignore_errors=True)

    def get_versions(self) -> Tuple[str, str]:
        """
        """
        self._write("Retrieving CS Tools metadata..")

        # retrieve for an existing install
        local_version = "0.0.0"

        if self.venv_path.exists():
            env = VirtualEnvironment(self.venv_path)
            cp  = env.python(
                      "-c", "import cs_tools;print(cs_tools.__version__)",
                      raise_on_failure=False
                  )

            if cp.returncode == 0:
                local_version = cp.stdout.decode().strip()

        if self._offline_install:
            fp = next(PKGS_DIR.glob('cs_tools*.whl'))
            # reliable because whl files have name conformity
            # <snake_case_pkg_name>-<version>-<platform-triplet>.whl
            # where platform triplet is <pyversion>-<abi>-<platform>
            # dots (.) in filename represent an OR relationship
            _, remote_version, *_ = fp.stem.split('-')
        else:
            metadata = json.loads(http_get(self.LATEST_RELEASE_METADTA).decode())
            remote_version = metadata["tag_name"]

        xm = VERSION_REGEX.match(local_version)
        x = (*xm.groups()[:3], xm.groups()[4])

        ym = VERSION_REGEX.match(remote_version)
        y = (*ym.groups()[:3], ym.groups()[4])

        # self._cursor.move_up()
        # self._cursor.clear_line()
        return '{}'.format('.'.join(x)), '{}'.format('.'.join(y))

    def ensure_directories(self) -> None:
        """
        """
        self._cs_tools_cfg_dir.mkdir(parents=True, exist_ok=True)
        self._executable_dir.mkdir(parents=True, exist_ok=True)

    def install_cs_tools(self, version, env):
        """
        """
        self._install_comment(version, "Installing CS Tools")

        if not self._offline_install:
            # fetch latest version from github
            # do some notifying that user is installing/upgrading their tools
            #
            raise NotImplementedError('coming soon...')
            return

        # poetry generates a list of packages which are required for cs_tools successful
        # installation, but not cs_tools itself (since poetry itself handles that bit).
        # take a 2-step process of installing all the dependencies, and then install
        # the cs_tools package.
        common = ["--find-links", PKGS_DIR.as_posix(), "--no-index", "--no-deps"]
        env.pip("install", "-r", (PKGS_DIR / "requirements.txt").as_posix(), *common)
        env.pip("install", f"cs_tools=={version}", *common)

    def create_executable(self, version, env):
        """
        """
        self._install_comment(version, "Creating script")

        for script in entrypoints_from_whl(next(PKGS_DIR.glob('cs_tools*.whl'))):
            # script = "cs_tools"
            script_bin = "bin"

            if WINDOWS:
                script += ".exe"
                script_bin = "Scripts"

            target_script = env.path.joinpath(script_bin, script)

            if self._executable_dir.joinpath(script).exists():
                self._executable_dir.joinpath(script).unlink()

            try:
                print(self._executable_dir.joinpath(script))
                self._executable_dir.joinpath(script).symlink_to(target_script)
            except OSError:
                # This can happen if the user
                # does not have the correct permission on Windows
                shutil.copy(target_script, self._executable_dir.joinpath(script))

    def run(self) -> int:
        """
        """
        self._write("")
        local, remote = self.get_versions()

        if self._reinstall:
            pass
        elif compare_versions(local, remote) >= 0:
            self._write('You have the latest version of CS Tools already!\n')
            return 0

        # self.display_pre_message()
        self.ensure_directories()

        try:
            self.install(remote)
        except sp.CalledProcessError as e:
            raise CSToolsActivatorError(
                return_code=e.returncode,
                log=e.output.decode()
            )

        self._write("")
        # self.display_post_message(local)
        return 0

    def install(self, version: str) -> int:
        """
        """
        self._write("Installing {} ({})".format("CS Tools", version))

        with self.make_env(version) as env:
            self.install_cs_tools(version, env)
            self.create_executable(version, env)
            self._install_comment(version, "Done")
            return 0

    # def uninstall(self) -> int:
    #     ...

    def activate(self) -> int:
        """
        Activate the virtual environment.
        """
        return VirtualEnvironment(self.venv_path).activate()
