from pathlib import Path
import sys
import os
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
HOME = Path("~").expanduser()
PKGS = Path(__file__).parent.parent / "pkgs"

WINDOWS = sys.platform == "win32"
MACOSX = sys.platform == "darwin"
SHELL = os.getenv("SHELL", "")

VERSION_REGEX = re.compile(
    r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?"
    "("
    "[._-]?"
    r"(?:(stable|beta|b|rc|RC|alpha|a|patch|pl|p)((?:[.-]?\d+)*)?)?"
    "([.-]?dev)?"
    ")?"
    r"(?:\+[^\s]+)?"
)

POST_MESSAGE = """CS Tools ({version}) is installed now. Great!

You can test that everything is set up by executing:

  {green}cs_tools --version{reset}
"""

POST_MESSAGE_NOT_IN_PATH = """CS Tools ({version}) is installed now. Great!

To get started you need CS Tools's bin directory ({sys_exe_dir}) in your `PATH`
environment variable.
{configure_message}
Alternatively, you can call CS Tools explicitly with {green}{executable}{note}.

You can test that everything is set up by executing:

  {green}cs_tools --version{reset}
"""

POST_MESSAGE_CONFIGURE_UNIX = """
{yellow}You might first try running {green}exec "$SHELL"{yellow} to refresh your shell.{note}

If that doesn't work, add {green}export PATH="{sys_exe_dir}:$PATH"{note} to your shell configuration file.
"""

POST_MESSAGE_CONFIGURE_FISH = """
You can execute {green}set -U fish_user_paths {sys_exe_dir} $fish_user_paths
"""
