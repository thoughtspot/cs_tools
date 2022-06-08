import pathlib
import sys
import os
import re


PKGS_DIR = pathlib.Path(__file__).parent.parent / 'pkgs'
WINDOWS = sys.platform.startswith("win") or (sys.platform == "cli" and os.name == "nt")
MACOS = sys.platform == "darwin"

VERSION_REGEX = re.compile(
    r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?"
    "("
    "[._-]?"
    r"(?:(stable|beta|b|rc|RC|alpha|a|patch|pl|p)((?:[.-]?\d+)*)?)?"
    "([.-]?dev)?"
    ")?"
    r"(?:\+[^\s]+)?"
)

PRE_MESSAGE = """# Welcome to {cs_tools}!

This will install the latest version of {cs_tools}, a command line utility written by
the ThoughtSpot Professional Services & Customer Success teams, meant to augment
built-in platform tools, help with administration of and enhance adoption within your
ThoughtSpot environment.

Learn more about the tools in our documentation:
https://cs_tools.thoughtspot.com
"""

POST_MESSAGE = """{cs_tools} ({version}) is installed now. Great!

You can test that everything is set up by executing:

`{test_command}`
"""
