"""
Contains code for the CS Tools Bootstrapper.

This code must stay within the python standard library and be python 3.9+ compliant.

Some of the imports look funny as hell, but essentially we delay them as late as
possible so we don't need to worry about something not being available on an
under-supported version of Python.
"""
from argparse import RawTextHelpFormatter
import argparse
import datetime as dt
import logging
import logging.config
import os
import platform
import shutil
import sys
import sysconfig
import textwrap
import typing

_LOG = logging.getLogger("cs_tools.bootstrapper")
__version__ = "1.0.2"
__minimum_python_version__ = (3, 9)


def cli():
    """Command line interface for setting up the CS Tools environment."""
    import pathlib

    parser = argparse.ArgumentParser(
        prog="CS Tools Bootstrapper",
        formatter_class=RawTextHelpFormatter,
        description=textwrap.dedent(
            """
            Installs, removes, or updates to the latest version of cs_tools

            Feeling lost? Try our tutorial!
            {c}https://thoughtspot.github.io/cs_tools/tutorial/{x}
            """
            .format(c=_BLUE, x=_RESET)
        ),
    )
    parser.add_argument(
        "--beta",
        help=argparse.SUPPRESS,
        # Install a remote pre-release version of CS Tools (can be any Github REF).
        # python -m _bootstrapper.py --beta v1.6.0
        # python -m _bootstrapper.py --beta dev
        # python -m _bootstrapper.py --beta 011c470e14fc780d3cdeb78553ef3e28de591a5e
        dest="beta",
        default=None,
    )
    parser.add_argument(
        "--dev",
        help=argparse.SUPPRESS,
        # Links your global cs_tools environment to the editable project.
        # For Developers: uv run python ./cs_tools/updater/_bootstrapper.py --dev --reinstall
        dest="dev",
        action="store_true",
    )
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument(
        "-i",
        "--install",
        help="Install cs_tools to your system {g}(default option){x}.".format(g=_GREEN, x=_RESET),
        dest="install",
        action="store_true",
        default=False,
    )
    operation.add_argument(
        "-r",
        "--reinstall",
        help="Destroy the existing virtual environment before installing CS Tools.",
        dest="reinstall",
        action="store_true",
        default=False,
    )
    operation.add_argument(
        "-u",
        "--uninstall",
        help="Remove cs_tools from your system, including your existing config files.",
        dest="uninstall",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Increase log verbosity level.",
        dest="verbose",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--offline-mode",
        help="Install cs_tools from a local distributable instead of from Github.",
        dest="offline_mode",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--proxy",
        help="URL to route through {p}fmt{x} http://[user:password@]proxy.server:port".format(p=_PURPLE, x=_RESET),
        dest="proxy",
        default=None,
    )
    parser.add_argument(
        "--no-clean",
        help="Don't attempt to clean up the temporary BOOTSTRAPPER files.",
        dest="pre_clean",
        action="store_false",
        default=True,
    )

    args = parser.parse_args()

    _setup_logging(args.verbose)

    # REMOVE ANY PRE-EXISTING WORK FROM A HISTORICAL INSTALL
    if args.pre_clean:
        _cleanup()

    _LOG.info(
        textwrap.dedent(
            """
            {g}Welcome to the CS Tools Bootstrapper!{x}

            {y}If you run into any issues, please reach out to us on GitHub Discussions below.{x}

                    GitHub: {b}{github_issues}{x}
            """
            .format(
                b=_BLUE,
                g=_GREEN,
                y=_YELLOW,
                x=_RESET,
                github_issues="https://github.com/thoughtspot/cs_tools/issues/new/choose",    
            )
        )
    )

    _LOG.debug(
        textwrap.dedent(
            """
            [PLATFORM DETAILS]
            Python Version: {py_version}
               System Info: {system} (detail: {detail})
             Platform Tags: {platform_tag}
                    Ran at: {now}
            
            """
            .format(
                system=platform.system(),
                detail=platform.platform(),
                platform_tag=sysconfig.get_platform(),
                py_version=platform.python_version(),
                now=dt.datetime.now(tz=dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S %z"),
            )
        )
    )

    try:
        CSToolsVenv = ensure_import_cs_tools_venv(ref=args.beta)

        if args.uninstall:
            _LOG.info("Uninstalling CS Tools, all its dependencies, and deleting your existing config files.")

            # REMOVE THE PATH MODIFICATIONS
            CSToolsVenv(base_dir=CSToolsVenv.default_base_path()).path_manipulator.uninstall()

            # REMOVE THE WHOLE ENVIRONMENT.
            shutil.rmtree(CSToolsVenv.default_base_path(), ignore_errors=True)

            _LOG.info("{c}Done!{x} Thank you for trying CS Tools.".format(c=_GREEN, x=_RESET))
            return 0

        # MAKE THE CS Tools ENVIRONMENT
        venv = CSToolsVenv.make(
            venv_directory=CSToolsVenv.default_base_path(),
            reset_venv=args.reinstall,
            offline_index=pathlib.Path(__file__).parent if args.offline_mode else None,
            proxy=args.proxy,
        )

        if args.dev:
            _LOG.info("Installing locally using the development environment.")
            _PROJ_ROOT = pathlib.Path(__file__).parent.parent.parent
            assert (_PROJ_ROOT / "pyproject.toml").exists(), "This should only be run within a Development Environment."
            where = _PROJ_ROOT.as_posix()
        elif args.offline_mode:
            wheel = next(p for p in pathlib.Path(__file__).parent.glob("cs_tools-*") if p.suffix in (".whl", ".zip"))
            where = wheel.as_posix()
        elif args.beta:
            _LOG.info("Installing CS Tools from ref {p}{tag}{x}.".format(p=_PURPLE, tag=args.beta, x=_RESET))
            where = "https://github.com/thoughtspot/cs_tools/archive/{tag}.zip".format(tag=args.beta)
        else:
            _LOG.info("Fetching the latest CS Tools release.")
            latest = get_latest_cs_tools_release()
            _LOG.info("Installing CS Tools from ref {p}{tag}{x}.".format(p=_PURPLE, tag=latest["tag_name"], x=_RESET))
            where = "https://github.com/thoughtspot/cs_tools/archive/{tag}.zip".format(tag=latest["tag_name"])

        # INSTALL CS Tools ITSELF.
        venv.install(package_spec="cs_tools[cli] @ {location}".format(location=where), editable=args.dev)

        # ADD THE PATH MODIFICATIONS.
        venv.path_manipulator.install()

        _LOG.info(
            textwrap.dedent(
                """
                {y}You're almost there! Please {g}restart your shell{x} {y}and then execute the command below.{x}
                
                {b}cs_tools --version{x}
                """
                .format(b=_BLUE, g=_GREEN, y=_YELLOW, x=_RESET)
            )
        )

    except Exception:
        raise

    else:
        _cleanup()

    return 0


# ======================================================================================================================
# UTILITIES required only by bootstrapper
# ======================================================================================================================


def _create_color_code(color, bold=False):
    # types: (str, bool) -> str
    # See: https://stackoverflow.com/a/33206814
    escape_sequence = "\033["
    end_sequence = "m"

    foreground_color_map = {
        "reset": 0,
        "black": 30,  # dark gray
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "magenta": 35,
        "cyan": 36,
        "white": 37,
    }

    if color not in foreground_color_map:
        raise ValueError("invalid terminal color code: '{c}'".format(c=color))

    to_bold = int(bold)  # 0 = reset , 1 = bold
    to_color = foreground_color_map[color]
    return escape_sequence + str(to_bold) + ";" + str(to_color) + end_sequence


_WHITE = _create_color_code("white")
_BLACK = _create_color_code("black", bold=True)
_BLUE = _create_color_code("blue", bold=True)
_GREEN = _create_color_code("green", bold=True)
_RED = _create_color_code("red", bold=True)
_PURPLE = _create_color_code("magenta", bold=True)
_YELLOW = _create_color_code("yellow", bold=True)
_RESET = _create_color_code("reset")


def _setup_logging(verbose=True):
    # types: (bool) -> None
    import pathlib
    import tempfile

    temp_fpname = tempfile.NamedTemporaryFile().name
    random_name = pathlib.Path(temp_fpname).name
    random_path = pathlib.Path.cwd().joinpath("cs_tools-bootstrap-error-{n}.log".format(n=random_name))

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "pretty": {
                "()": lambda: ColorSupportedFormatter(datefmt="%H:%M:%S"),
            },
            "detail": {
                "format": "%(levelname)-8s | %(asctime)s | %(filename)s:%(lineno)d | %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": logging.INFO if not verbose else logging.DEBUG,
                "formatter": "pretty",
            },
            "disk": {
                "()": lambda: InMemoryUntilErrorHandler(filename=random_path),
                "level": "DEBUG",
                "formatter": "detail",
            },
        },
        "loggers": {
            "root": {
                "level": "DEBUG",
                "handlers": [
                    "console",
                    "disk",
                ],
            }
        },
    }

    logging.config.dictConfig(config)


class ColorSupportedFormatter(logging.Formatter):
    """
    Fancy formatter, intended for output to a terminal.

    The log record format itself is fairly locked to look like..

     11:13:51 | Welcome to the CS Tools Installation script!
              |
              |     [PLATFORM DETAILS]
              |     system: Windows (detail: Windows-10-10.0.19041-SP0)
              |     platform tag 'win-amd64'
              |     python: 3.10.4
              |     ran at: 2022-06-12 11:13:51
              |

    Parameters
    ----------
    skip_common_time: bool  [default: True]
      whether or not to repeat the same time format for each line

    **passthru
      keywords to send to logging.Formatter
    """

    COLOR_CODES = {  # noqa: RUF012
        logging.CRITICAL: _PURPLE,
        logging.ERROR: _RED,
        logging.WARNING: _YELLOW,
        logging.INFO: _WHITE,
        logging.DEBUG: _BLACK,
    }

    def __init__(self, skip_common_time=True, **passthru):
        # types: (bool, **passthru) ->  None
        passthru["fmt"] = "%(asctime)s %(color_code)s| %(indent)s%(message)s%(color_reset)s"
        super().__init__(**passthru)
        self._skip_common_time = skip_common_time
        self._last_time = None
        self._original_datefmt = str(self.datefmt)
        self._try_enable_ansi_terminal_mode()

    def _try_enable_ansi_terminal_mode(self):
        # See: https://stackoverflow.com/a/36760881
        if not sys.platform == "win32":
            return

        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    def format(self, record, *a, **kw):
        # types: (logging.LogRecord, a, **kw) -> str
        color = self.COLOR_CODES.get(record.levelno, _create_color_code("white"))
        record.color_code = color
        record.color_reset = _create_color_code("reset")
        record.indent = ""

        # skip repeating the time format if it hasn't changed since last log
        formatted_time = self.formatTime(record, self._original_datefmt)

        if self._skip_common_time:
            if self._last_time == formatted_time:
                self.datefmt = len(formatted_time) * " "
            else:
                self.datefmt = self._original_datefmt
                self._last_time = formatted_time

        # force newlines to respect indentation
        record.message = record.getMessage()
        record.asctime = formatted_time
        s = self.formatMessage(record)
        prefix, _, _ = s.partition(record.msg[:10])
        prefix = prefix.replace(formatted_time, len(formatted_time) * " ")
        record.msg = record.msg.replace("\n", "\n{p}".format(p=prefix))

        return super().format(record, *a, **kw)


class InMemoryUntilErrorHandler(logging.FileHandler):
    """
    A handler which stores lines in memory until an error is reached,
    and only then writes to file.

    If no error is reached during execution of the program, a logfile will not
    be generated. Once the first error is found, the entire buffer will drain
    into the logfile, with the error itself being the final stub of the file.

    Parameters
    ----------
    filename: pathlib.Path
      name of the file to write logs to

    **passthru
      keywords to send to logging.FileHandler
    """

    def __init__(self, filename, **passthru):
        # types: (pathlib.Path, **passthru) -> None
        super().__init__(filename, delay=True, **passthru)
        self._buffer = []
        self._found_error = False

    def drain_buffer(self):
        # types: () -> None
        """Emit all the existing log lines."""
        self._found_error = True

        for prior_record in self._buffer:
            super().emit(prior_record)

        self._buffer.clear()

    def emit(self, record):
        """Conditionally emit/store a line based on presence of any errors."""
        # types: (logging.LogRecord) -> None
        if self._found_error:
            super().emit(record)
            return

        if record.levelno < logging.ERROR:
            self._buffer.append(record)
            return

        self.drain_buffer()
        super().emit(record)


def _cleanup():
    # type: () -> None
    """Remove temporary files for bootstrapping the CS Tools environment."""
    import pathlib

    HERE = pathlib.Path(__file__).parent
    FILES_TO_CLEAN = ("__pycache__", "_updater.py", "_bootstrapper.py")

    # DON'T RUN THE CLEANUP STEP WITHIN THE DEVELOPMENT ENVIRONMENT
    if "updater" in HERE.as_posix():
        return

    for stem in FILES_TO_CLEAN:
        path = HERE / stem

        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)

        if path.is_file():
            path.unlink(missing_ok=True)


def ensure_import_cs_tools_venv(ref=None):  # type: ignore[name-defined]
    # type: (str | None) -> cs_tools.updater._updater.CSToolsVenv
    """Get the CS Tools Virtual Environment."""
    import pathlib

    HERE = pathlib.Path(__file__).parent
    UPDATER_PY = HERE / "_updater.py"

    # DOWNLOAD IT FROM GITHUB.
    if not UPDATER_PY.exists():
        _LOG.info("Missing '{py}', downloading from GitHub".format(py=UPDATER_PY))

        base = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        endp = base.format(owner="thoughtspot", repo="cs_tools", path="cs_tools/updater/_updater.py")

        if ref is not None:
            endp += "?ref={ref}".format(ref=ref)

        # FETCH FILE METADATA.
        meta = http_request(endp, to_json=True)
        assert isinstance(meta, dict), "Github API returned invalid data for file metadata:\n{d!r}".format(d=meta)

        # FETCH THE FILE ITSELF.
        data = http_request(meta["download_url"], to_json=False)
        assert isinstance(data, bytes), "Github API returned invalid data for file download:\n{d!r}".format(d=data)

        # FETCH THE FILE ITSELF.
        UPDATER_PY.write_bytes(data)
        _LOG.info("Downloaded as '{py}'".format(py=UPDATER_PY))

    try:
        # Hack the PATH var so we can import from _updater
        sys.path.insert(0, HERE.as_posix())

        from _updater import CSToolsVenv  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        _LOG.error(
            textwrap.dedent(
                """
                Unable to find the CS Tools _updater.py, try downloading it from GitHub:
    
                    {b}{file_location}{x}
                
                ..and place it in this directory:

                    {b}{here}{x}
                
                ..then re-run the bootstrapper with the {p}--no-clean{x} option.
                """
                .format(b=_BLUE, file_location=meta["download_url"], here=HERE, p=_PURPLE, x=_RESET)
            )
        )
        
        raise
    finally:
        sys.path.remove(HERE.as_posix())

    return CSToolsVenv


def http_request(url, to_json=True, timeout=None):
    # type: (str, bool, float | None) -> dict[str, typing.Any] | bytes
    """Makes a GET request to <url>."""
    import json
    import ssl
    import urllib.request
    import urllib.error
    import urllib

    ctx = ssl.create_default_context()

    # ssl.OP_LEGACY_SERVER_CONNECT is missing until py3.12
    #
    # Further Reading:
    #   https://bugs.python.org/issue44888
    OP_LEGACY_SERVER_CONNECT = 0x4
    ctx.options |= OP_LEGACY_SERVER_CONNECT

    # DISABLE SSL VERFICATION CHECKS.
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        _LOG.debug("Making HTTP GET {u}".format(u=url))

        with urllib.request.urlopen(url, timeout=timeout, context=ctx) as r:
            data = r.read()

        if to_json:
            data = json.loads(data)

    except urllib.error.HTTPError:
        _LOG.error("Something went wrong when requesting: {u}".format(u=url))
        _LOG.debug("urllib.error.HTTPError stack", exc_info=True)
        raise

    except json.JSONDecodeError:
        _LOG.error("Something went wrong when parsing response data: {u}".format(u=url))
        _LOG.debug("Data\n%s", data, exc_info=True)
        raise

    return data


def get_latest_cs_tools_release(timeout=None):
    # type: (float | None) -> dict[str, typing.Any]
    """Gets the latest CS Tools release."""
    base = "https://api.github.com/repos/{owner}/{repo}/releases/latest"
    endp = base.format(owner="thoughtspot", repo="cs_tools")

    data = http_request(endp, timeout=timeout)
    assert isinstance(data, dict), "http_request didn't return valid JSON, got '{!r}".format(data)

    return data


# ======================================================================================================================
# MAIN PROGRAM
# ======================================================================================================================

def main():
    # type: () -> int
    """The main entrypoint for the CS Tools bootstrapper."""
    return_code = 0  # SUCCESS

    # =================================================
    # MINIMUM PYTHON VERSION CHECK FAILED.
    # =================================================
    if sys.version_info < __minimum_python_version__:
        return_code = 1

        message = textwrap.dedent(
            """
            {y}It looks like you are running {r}Python v{version}{y}!{x}
            
            CS Tools supports {b}python version {minimum_support}{x} or greater.
            """
        )

        if sys.platform != "win32":
            message += textwrap.dedent(
                """
                {b}Please re-run the following command..{x}

                python3 {args}
                """
            )
        else:
            message += textwrap.dedent(
                """
                {y}Python installers are available for download for all versions at..{x}
                {b}https://www.python.org/downloads/{x}
                """
            )

        print(
            textwrap.dedent(
                message.format(
                    b=_BLUE,
                    r=_RED,
                    y=_YELLOW,
                    x=_RESET,
                    version=".".join(map(str, sys.version_info[:2])),
                    minimum_support=".".join(map(str, __minimum_python_version__)),
                    args=" ".join(map(str, sys.argv)),
                )
            )
        )

        return return_code
    
    # =================================================
    # ANACONDA ENVIRONMENTS ARE ALREADY ISOLATED.
    # =================================================
    elif "CONDA_DEFAULT_ENV" in os.environ and "CS_TOOLS_IGNORE_CONDA_PATH" not in os.environ:
        return_code = 1

        print(
            textwrap.dedent(
                """
                {y}It looks like you are running in an Anaconda environment!{x}
                
                {r}Installation and execution of CS Tools within conda is not well tested and may lead to issues.{x}
                
                Please deactivate the environment and run again.
                  {g}See{x} https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#deactivating-an-environment
                
                To ignore this warning, set the environment variable {b}CS_TOOLS_IGNORE_CONDA_PATH{x} to any value.
                """
                .format(
                    b=_BLUE,
                    g=_GREEN,
                    r=_RED,
                    y=_YELLOW,
                    x=_RESET,
                )
            )
        )

        return return_code

    # =================================================
    # BASIC CHECKS PASSED, ATTEMPT CREATION AND INSTALL
    # =================================================

    try:
        return_code = cli()

    except Exception as e:
        disk_handler = next(h for h in _LOG.root.handlers if isinstance(h, InMemoryUntilErrorHandler))
        _LOG.debug("Error found: {err}".format(err=e), exc_info=True)
        _LOG.error(
            "Unexpected error in bootstrapper, see {b}{logfile}{x} for details..".format(
                b=_BLUE, logfile=disk_handler.baseFilename, x=_YELLOW
            )
        )
        return_code = 1

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
