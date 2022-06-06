from pathlib import Path
from typing import Tuple
import subprocess as sp
import traceback
import tempfile
import pathlib

from _installer import Installer, ReturnCode
from _errors import CSToolsInstallationError
from _const import WINDOWS
from _util import app_dir


def run(args: Tuple[str]) -> ReturnCode:

    if args.activate:
        cs_tools_venv = pathlib.Path(app_dir()) / '.cs_tools'

        if WINDOWS:
            bin_ = (cs_tools_venv / 'Scripts' / 'activate.ps1').as_posix()
            cmd = (
                'powershell -ExecutionPolicy Bypass -NoExit -NoLogo -Command { '
                + bin_ + " ; cs_tools }"
            )
        else:
            cmd = 'source ' + (cs_tools_venv / 'bin' / 'activate').as_posix() + ' cs_tools'

        msg = """
        Copy and paste this command into your terminal. You'll know you've done it
        correctly if the prompt starts with (.cs_tools)

        Leave the CLI at any time by simply typing "deactivate".

        {cmd}
        """
        print(msg.format(cmd=cmd))
        return 0

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
