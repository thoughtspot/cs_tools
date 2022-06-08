from urllib.request import Request, urlopen
from contextlib import closing
from pathlib import Path
import sys
import os

from _const import WINDOWS, MACOSX, VERSION_REGEX


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


def app_dir(app_name: str) -> Path:
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
        folder = os.environ.get("APPDATA") or os.path.expanduser("~")
        return Path(folder).joinpath(app_name)

    if MACOSX:
        home_app_support = os.path.expanduser("~/Library/Application Support")
        return Path(home_app_support).joinpath(app_name)

    home_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(home_config).joinpath(_posixify(app_name))


def compare_versions(x: str, y: str) -> int:
    """
    Determine the relationship between two version strings.

    -1 means the source version is less than the target
     0 means the source and target versions are equal
     1 means the source version is greater than the target
    """
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
