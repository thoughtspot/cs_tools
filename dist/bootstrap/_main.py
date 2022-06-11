"""
Making it here ensures we have a python 3.6.8-enabled installation.
"""
from pathlib import Path
from typing import Tuple
import logging

from _activator import Activator
from _logging import ColorSupportedFormatter, InMemoryUntilErrorHandler
from _errors import CSToolsActivatorError


log = logging.getLogger(__name__)


def run(args: Tuple[str]) -> int:
    """
    Run the CS Tools installer.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # CONSOLE LOGGER IS PRETTY
    handler = logging.StreamHandler()
    format_ = ColorSupportedFormatter(fmt="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(format_)
    handler.setLevel(logging.INFO)
    root.addHandler(handler)

    # FILE LOGGER IS VERBOSE
    handler = InMemoryUntilErrorHandler(directory=Path.cwd(), prefix="cs_tools-installer-error-")
    format_ = logging.Formatter(fmt="%(levelname)-8s | %(asctime)s | %(filename)s:%(lineno)d | %(message)s")
    handler.setFormatter(format_)
    handler.setLevel(logging.DEBUG)
    root.addHandler(handler)

    log.info('Welcome to the CS Tools Installation script!')

    activator = Activator(
        offline_install=not args.fetch_remote,
        reinstall=args.reinstall,
    )

    try:
        rc = activator.run()

    except CSToolsActivatorError as e:
        rc = e.returncode
        log.error("CSTools installation failed.")

    except Exception as e:
        rc = 1
        log.error(f'Unplanned error: {e}')
        log.debug('full traceback..', exc_info=True)

    if rc != 0:
        log.error(f"See '{handler.baseFilename}' for error logs.")

    return rc
