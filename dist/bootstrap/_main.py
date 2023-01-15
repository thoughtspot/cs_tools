"""
Making it here ensures we have a python 3.6.8-enabled installation.
"""
from pathlib import Path
import datetime as dt
import sysconfig
import argparse
import platform
import logging

from _activator import Activator
from _logging import ColorSupportedFormatter, InMemoryUntilErrorHandler, add_logging_level
from _errors import CSToolsActivatorError
from _types import ReturnCode


log = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> ReturnCode:
    """
    Run the CS Tools installer.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    add_logging_level("NOTE", logging.INFO + 5)

    # CONSOLE LOGGER IS PRETTY
    handler = logging.StreamHandler()
    format_ = ColorSupportedFormatter(datefmt="%H:%M:%S")
    format_.add_color_level(logging.NOTE, color="blue", bold=True)
    handler.setFormatter(format_)
    handler.setLevel(logging.INFO if not args.verbose else logging.DEBUG)
    root.addHandler(handler)

    # FILE LOGGER IS VERBOSE
    handler = InMemoryUntilErrorHandler(directory=Path.cwd(), prefix="cs_tools-bootstrap-error-")
    format_ = logging.Formatter(fmt="%(levelname)-8s | %(asctime)s | %(filename)s:%(lineno)d | %(message)s")
    handler.setFormatter(format_)
    handler.setLevel(logging.DEBUG)
    root.addHandler(handler)

    log.info("Welcome to the CS Tools Installation script!")
    log.debug(
        f"""
    [PLATFORM DETAILS]
    system: {platform.system()} (detail: {platform.platform()})
    platform tag '{sysconfig.get_platform()}'
    python: {platform.python_version()}
    ran at: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}
    """
    )

    activator = Activator(
        # offline_install=not args.fetch_remote,
        offline_install=True,
        reinstall=args.reinstall,
        setup=args.setup,
    )

    if not args.setup and "macOS" in platform.platform() and "arm64" in platform.platform():
        log.note(
            "You've got one of those fancy new Apple M1 chips! Unfortunately, CS Tools doesn't "
            "yet support offline installs for this chipset yet. For the time being, you'll have "
            "to follow these manual instructions first."
        )
        log.info(
            "\n"
            "\n  # Change directory to the CS Tools internal application directory."
            '\n  cd "$HOME/Library/Application Support/cs_tools"'
            "\n"
            "\n  # Create a virtual environment called .cs_tools"
            "\n  python3 -m venv .cs_tools"
            "\n"
            "\n  # Activate that virtual environment."
            '\n  source "$HOME/Library/Application Support/cs_tools/.cs_tools/bin/activate"'
            "\n"
            "\n  # Install the CS Tools dependencies remotely."
            "\n  pip install -r $HOME/Downloads/cs_tools-bootstrapper/pkgs/requirements.txt"
            "\n"
            "\n  # Change directory back to the Downloads folder."
            "\n  cd -"
            "\n"
            "\n  # Install CS Tools itself, ignoring the remote python package index."
            "\n  pip install cs_tools --upgrade --find-links pkgs/ --no-index"
            "\n"
            "\n  # Deactivate the virtual environment."
            "\n  deactivate"
            "\n"
            "\n  # Setup the rest of the CS Tools application."
            "\n  python bootstrap --setup"
        )
        return 0

    try:
        # if args.uninstall:
        #     return activator.uninstall()

        if args.check_version:
            local, remote = activator.get_versions()
            local = "none installed" if local == "0.0.0." else local
            loc = "offline" if activator._offline_install else " online"
            log.note(f"Your installed version: {local}\nLatest {loc} version: {remote}")
            return 0

        rc = activator.run()

    except CSToolsActivatorError as e:
        rc = e.return_code
        _priority_list = {
            # 'uninstall': 'uninstallation',
            "check_version": "check-version",
            "reinstall": "reinstallation",
        }

        for arg, operation in _priority_list.items():
            if getattr(args, arg):
                break
        else:
            operation = "installation"

        log.error(f"CS Tools {operation} failed.")
        log.debug(f"full traceback..\nReason: {e.log}---\n\n", exc_info=True)

    except Exception as e:
        rc = 1
        log.error(f"Unplanned error: {e}")
        log.debug("full traceback..", exc_info=True)

    if rc != 0:
        log.warning(f"See '{handler.baseFilename}' for error logs.")

    return rc
