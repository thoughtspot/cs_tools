import sys
import re


WINDOWS = sys.platform == "win32"

VERSION_REGEX = re.compile(
    r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?"
    "("
    "[._-]?"
    r"(?:(stable|beta|b|rc|RC|alpha|a|patch|pl|p)((?:[.-]?\d+)*)?)?"
    "([.-]?dev)?"
    ")?"
    r"(?:\+[^\s]+)?"
)
