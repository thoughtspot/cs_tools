"""
This is the entrypoint guard for the CS Tools Activator.

Linux/Mac environments may accidentally run this from the global python
environment, which is occasionally still py-2.7 , we need this script to
stay compatible so it can warn users and ask them re-run with python3.
"""
from argparse import RawTextHelpFormatter
import argparse
import platform
import textwrap
import sys
import os

try:
    from _types import ReturnCode
except ImportError:
    pass


_BLUE = "\033[1;34m"
_GREEN = "\033[1;32m"
_RED = "\033[1;31m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"
SUPPORTED_MINIMUM_PYTHON = (3, 6, 8)

UNSUPPORTED_VERSION_MESSAGE = """
    {y}It looks like you are running {r}Python v{version}{y}!{x}

    {b}CS Tools only supports python version {min_python} or greater.{x}
{submessage}
"""


def main():  # type: () -> ReturnCode
    """
    Entrypoint.
    """
    parser = argparse.ArgumentParser(
        prog="CS Tools Bootstrapper",
        formatter_class=RawTextHelpFormatter,
        description=textwrap.dedent(
            """
        Installs, removes, or updates to the latest version of cs_tools
        
        Feeling lost? Try our tutorial!
        {c}https://thoughtspot.github.io/cs_tools/tutorial/{x}
        """.format(
                c=_BLUE, x=_RESET
            )
        ),
    )
    # parser.add_argument(
    #     "-f",
    #     "--fetch-remote",
    #     help="fetching the latest version of cs_tools available online",
    #     dest="fetch_remote",
    #     action="store_true",
    #     default=False
    # )
    parser.add_argument(
        "-c",
        "--check-version",
        help="check your version of CS Tools against the latest version",
        dest="check_version",
        action="store_true",
        default=False,
    )
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument(
        "-i",
        "--install",
        help="install cs_tools to your system {c}(default option){x}".format(c=_GREEN, x=_RESET),
        dest="install",
        action="store_false",
        default=True,
    )
    operation.add_argument(
        "-r",
        "--reinstall",
        help="install on top of existing version",
        dest="reinstall",
        action="store_true",
        default=False,
    )
    operation.add_argument("-s", "--setup", help=argparse.SUPPRESS, dest="setup", action="store_true", default=False)
    # operation.add_argument(
    #     "-u",
    #     "--uninstall",
    #     help="remove cs_tools from your system",
    #     dest="uninstall",
    #     action="store_true",
    #     default=False,
    # )
    parser.add_argument(
        "-v",
        "--verbose",
        help="increase terminal output level",
        dest="verbose",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()
    py_version = tuple(map(int, platform.python_version().split(".")))

    # short circuit and run the cli if we're in a supported environment
    if py_version >= SUPPORTED_MINIMUM_PYTHON:
        import _main

        return _main.run(args)

    if py_version <= (2, 7, 99) and os.environ.get("SHELL", False):
        args = " ".join(map(str, sys.argv))
        msg = """
        {b}Please re-run the following command..{x}

        python3 {args}
        """.format(
            args=args, b=_BLUE, x=_RESET
        )
    else:
        msg = ""

    template = {
        "b": _BLUE,
        "r": _RED,
        "y": _YELLOW,
        "x": _RESET,
        "version": ".".join(map(str, py_version)),
        "min_python": ".".join(map(str, SUPPORTED_MINIMUM_PYTHON)),
        "submessage": msg,
    }
    print (UNSUPPORTED_VERSION_MESSAGE.format(**template))  # fmt: skip
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
