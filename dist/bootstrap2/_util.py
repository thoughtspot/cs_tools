from urllib.request import Request, urlopen
from contextlib import closing
from pathlib import Path
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


def app_dir(app_name: str = 'cs_tools') -> str:
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
            folder = os.path.expanduser("~")
        return os.path.join(folder, app_name)

    if sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~/Library/Application Support"), app_name
        )

    return os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
        _posixify(app_name),
    )


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
