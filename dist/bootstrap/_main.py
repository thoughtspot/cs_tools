"""
Making it here ensures we have a python 3.6.8-enabled installation.
"""
from pathlib import Path
from typing import Tuple
import traceback
import tempfile

from _activator import Activator
from _errors import CSToolsActivatorError


def run(args: Tuple[str]):
    activator = Activator(
        offline_install=not args.fetch_remote,
        reinstall=args.reinstall,
    )

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
