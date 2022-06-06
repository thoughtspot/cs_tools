import argparse
import platform
import sys


SUPPORTED_MINIMUM_PYTHON = (3, 6, 8)


def main():
    """
    Entrypoint.
    """
    parser = argparse.ArgumentParser(description="Installs the latest version of cs_tools")
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
        "-a",
        "--activate",
        help="activate the CS Tools command line",
        dest="activate",
        action="store_true",
        default=False
    )

    args = parser.parse_args()

    if args.fetch_remote:
        print ("This operation is not yet supported. It's coming soon..!")
        return 1

    py_version = tuple(map(int, platform.python_version().split('.')))

    if py_version >= SUPPORTED_MINIMUM_PYTHON:
        import _main
        return _main.run(args)

    UNSUPPORTED_VERSION_MESSAGE = """
    It looks like you are running Python {version}!

    CS Tools only supports python version {min_python} or greater.
    {submessage}
    """

    if py_version <= (2, 7, 99):
        args = ' '.join(map(str, sys.argv))
        msg = """
        Please re-run the following command..

        python3 {args}
        """.format(args=args)
    else:
        pass

    template = {
        'version': '.'.join(map(str, py_version)),
        'min_python': '.'.join(map(str, SUPPORTED_MINIMUM_PYTHON)),
        'submessage': msg
    }
    print (UNSUPPORTED_VERSION_MESSAGE.format(**template))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
