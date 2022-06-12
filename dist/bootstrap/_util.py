from urllib.request import Request, urlopen
from contextlib import closing
from pathlib import Path
from typing import List
import zipfile
import site
import sys
import os

from _const import WINDOWS, VERSION_REGEX


def _posixify(name: str) -> str:
    """
    Turn a name into something that posix is happy with.

    Valid characters
    - Uppercase A to Z
    - Lowercase a to z
    - Numbers 0 to 9
    - Period (.)
    - Underscore (_)
    - Hyphen (-)
    """
    return "-".join(name.split()).lower()


def app_dir(app_name: str = "cs_tools") -> str:
    r"""
    Return the config folder for the application.

    The default behavior is to return whatever is most appropriate for
    the operating system.

    To give you an idea, for an app called ``"Foo Bar"``, something like
    the following folders could be returned:

        Mac OS X:
          ~/Library/Application Support/Foo Bar

        Mac OS X (POSIX):
          ~/.foo-bar

        Unix:
          ~/.config/foo-bar

        Unix (POSIX):
          ~/.foo-bar

        Windows (roaming):
          C:\Users\<user>\AppData\Roaming\Foo Bar
    """
    if WINDOWS:
        folder = os.environ.get("APPDATA")
        if folder is None:
            folder = Path("~").expanduser()
        return Path(folder).joinpath(app_name)

    if sys.platform == "darwin":
        return Path("~/Library/Application Support").expanduser().joinpath(app_name)

    home = os.environ.get("XDG_CONFIG_HOME", Path("~/.config").expanduser())
    return Path(home).joinpath(_posixify(app_name))


def bin_dir() -> Path:
    # if os.getenv("CS_TOOLS_HOME"):
    #     return Path(os.getenv("CS_TOOLS_HOME"), "bin").expanduser()

    user_base = site.getuserbase()
    return Path(user_base).joinpath("Scripts" if WINDOWS else "bin")


def compare_versions(x, y):
    mx = VERSION_REGEX.match(x)
    my = VERSION_REGEX.match(y)

    vx = tuple(int(p) for p in mx.groups()[:3]) + (mx.group(5),)
    vy = tuple(int(p) for p in my.groups()[:3]) + (my.group(5),)

    if vx < vy:
        return -1
    elif vx > vy:
        return 1

    return 0


def http_get(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "CS Tools"})

    with closing(urlopen(request)) as r:
        return r.read()


def entrypoints_from_whl(fp: Path) -> List[str]:
    entrypoints = []
    with zipfile.ZipFile(fp, mode="r") as zip_:
        file = next((f for f in zip_.namelist() if f.endswith("entry_points.txt")), None)

        if file is None:
            return []

        with zip_.open(file, mode="r") as f:
            for line in f:
                if "[console_scripts]" in line.decode():
                    continue

                command, _, _ = line.decode().strip().partition("=")

                if command:
                    entrypoints.append(command)

    return entrypoints
