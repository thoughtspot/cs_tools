"""
This is the entrypoint guard for the CS Tools Activator.

Linux/Mac environments may accidentally run this from the global python
environment, which is occasionally still py-2.7 , we need this script to
stay compatible so it can warn users and ask them re-run with python3.
"""
import argparse
import platform
import sys

try:
    from _types import ReturnCode
except ImportError:
    pass


_YELLOW = '\033[33m'
_BLUE = '\033[1;34m'
_MAGENTA = '\033[1;35m'
_RESET = '\033[0m'
SUPPORTED_MINIMUM_PYTHON = (3, 6, 8)

UNSUPPORTED_VERSION_MESSAGE = """
    {y}It looks like you are running {m}Python v{version}{y}!{c}

    {b}CS Tools only supports python version {min_python} or greater.{c}
{submessage}
"""


def main():  # type: () -> ReturnCode
    """
    Entrypoint.
    """
    parser = argparse.ArgumentParser(
        prog="CS Tools Bootstrapper",
        description="Installs, updates, or activates the latest version of cs_tools"
    )
    parser.add_argument(
        "-f",
        "--fetch-remote",
        help="fetching the latest version of cs_tools available online",
        dest="fetch_remote",
        action="store_true",
        default=False
    )
    parser.add_argument(
        "-r",
        "--reinstall",
        help="install on top of existing version",
        dest="reinstall",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="increase terminal output level",
        dest="verbose",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()
    py_version = tuple(map(int, platform.python_version().split('.')))

    # short circuit and run the cli if we're in a supported environment
    if py_version >= SUPPORTED_MINIMUM_PYTHON:
        import _main
        return _main.run(args)

    if py_version <= (2, 7, 99):
        args = ' '.join(map(str, sys.argv))
        msg = """
        {b}Please re-run the following command..{c}

        python3 {args}
        """.format(args=args, b=_BLUE, c=_RESET)
    else:
        msg = ''

    template = {
        'b': _BLUE,
        'c': _RESET,
        'm': _MAGENTA,
        'y': _YELLOW,
        'version': '.'.join(map(str, py_version)),
        'min_python': '.'.join(map(str, SUPPORTED_MINIMUM_PYTHON)),
        'submessage': msg
    }
    print (UNSUPPORTED_VERSION_MESSAGE.format(**template))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
