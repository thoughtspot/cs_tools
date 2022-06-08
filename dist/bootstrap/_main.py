"""
Making it here ensures we have a python 3.6.8-enabled installation.
"""
from pathlib import Path
from typing import Tuple
import subprocess as sp
import traceback
import tempfile
import pathlib

from _activator import Activator
from _errors import CSToolsActivatorError
from _const import WINDOWS
from _util import app_dir


def run(args: Tuple[str]):
    activator = Activator(
        offline_install=not args.fetch_remote,
        reinstall=args.reinstall,
    )

    if args.activate:
        # cs_tools_venv = pathlib.Path(app_dir()) / '.cs_tools'

        # if WINDOWS:
        #     bin_ = (cs_tools_venv / 'Scripts' / 'activate.ps1').as_posix()
        #     cmd = (
        #         'powershell -ExecutionPolicy Bypass -NoExit -NoLogo -Command { '
        #         + bin_ + " ; cs_tools }"
        #     )
        # else:
        #     cmd = 'source ' + (cs_tools_venv / 'bin' / 'activate').as_posix() + ' cs_tools'

        # msg = """
        # Copy and paste this command into your terminal. You'll know you've done it
        # correctly if the prompt starts with (.cs_tools)

        # Leave the CLI at any time by simply typing "deactivate".

        # {cmd}
        # """
        # print(msg.format(cmd=cmd))
        activator.activate()
        return 0

    try:
        return activator.run()
    except CSToolsActivatorError as e:
        activator._write("[ERROR] CSTools installation failed.")

        if e.log is not None:
            _, path = tempfile.mkstemp(suffix=".log", prefix="cs_tools-installer-error-", dir=str(Path.cwd()), text=True)
            activator._write(f"[ERROR] See {path} for error logs.")
            tb = ''.join(traceback.format_tb(e.__traceback__))
            Path(path).write_text(f"{e.log}\n\nTraceback:\n{tb}")

        return e.return_code
