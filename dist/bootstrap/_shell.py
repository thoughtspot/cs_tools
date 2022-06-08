from pathlib import Path
from typing import List
import subprocess
import signal
import sys
import os

from _virtual_env import VirtualEnvironment


class Shell:
    """
    Represents the current shell.
    """
    _shell = None

    def __init__(self, name: str, path: str) -> None:
        self._name = name
        self._path = path

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return self._path

    @classmethod
    def get(cls) -> Shell:
        """
        Retrieve the current shell.
        """
        if cls._shell is not None:
            return cls._shell

        shell = None

        if os.name == "posix":
            shell = os.environ.get("SHELL")
        elif os.name == "nt":
            shell = os.environ.get("COMSPEC")

        if not shell:
            raise RuntimeError("Unable to detect the current shell.")

        name, path = Path(shell).stem, shell
        cls._shell = cls(name, path)
        return cls._shell

    def command(self, env: VirtualEnv, *args: Tuple[str]) -> int:
        bin_dir = "Scripts" if WINDOWS else "bin"
        python = "python.exe" if WINDOWS else "python"
        activate_path = env.path / bin_dir / python
        args = [str(activate_path), *args]
        completed_proc = subprocess.run([self.path, *args])
        return completed_proc.returncode

    def activate(self, env: VirtualEnv) -> int:
        bin_dir = "Scripts" if WINDOWS else "bin"
        activate_script = self._get_activate_script()
        activate_path = env.path / bin_dir / activate_script

        # mypy requires using sys.platform instead of WINDOWS constant
        # in if statements to properly type check on Windows
        if sys.platform == "win32":
            if self._name in ("powershell", "pwsh"):
                args = ["-NoExit", "-File", str(activate_path)]
            else:
                # /K will execute the bat file and
                # keep the cmd process from terminating
                args = ["/K", str(activate_path)]
            completed_proc = subprocess.run([self.path, *args])
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

    def _get_activate_script(self) -> str:
        if self._name == "fish":
            suffix = ".fish"
        elif self._name in ("csh", "tcsh"):
            suffix = ".csh"
        elif self._name in ("powershell", "pwsh"):
            suffix = ".ps1"
        elif self._name == "cmd":
            suffix = ".bat"
        else:
            suffix = ""

        return "activate" + suffix

    def _get_source_command(self) -> str:
        if self._name in ("fish", "csh", "tcsh"):
            return "source"
        return "."

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self._name}", "{self._path}")'
