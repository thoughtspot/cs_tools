from pathlib import Path
import sys
import re

# CS ACTIVATOR DIRECTORY STRUCTURE LOOKS LIKE
#
#  dist/
#  ├─ bootstrap/
#  │  ├─ __init__.py
#  │  ├─ _const.py
#  │  └─ ...
#  └─ pkgs/
#     ├─ requirements.txt
#     ├─ click-X.Y.Z-py3-none-any.whl
#     ├─ httpx-X.Y.Z-py3-none-any.whl
#     ├─ ...
#     └─ cs_tools-{__version__}-py3-none-any.whl
#
PKGS_DIR = Path(__file__).parent.parent / 'pkgs'

WINDOWS = sys.platform == "win32"
MACOSX  = sys.platform == "darwin"

VERSION_REGEX = re.compile(
    r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?"
    "("
    "[._-]?"
    r"(?:(stable|beta|b|rc|RC|alpha|a|patch|pl|p)((?:[.-]?\d+)*)?)?"
    "([.-]?dev)?"
    ")?"
    r"(?:\+[^\s]+)?"
)
