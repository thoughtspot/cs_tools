"""
Do not rely on these. This is a legacy implementation of global context.

It will be refactored out.
"""

import pathlib


PACKAGE_DIR = pathlib.Path(__file__).parent
TOOLS_DIR = PACKAGE_DIR / "cli" / "tools"

# ISO datetime format
FMT_TSLOAD_DATE = "%Y-%m-%d"
FMT_TSLOAD_TIME = "%H:%M:%S"
FMT_TSLOAD_DATETIME = f"{FMT_TSLOAD_DATE} {FMT_TSLOAD_TIME}"
FMT_TSLOAD_TRUE_FALSE = "True_False"

DOCS_BASE_URL = "https://thoughtspot.github.io/cs_tools/"
GH_ISSUES = "https://github.com/thoughtspot/cs_tools/issues/new/choose"
GH_SYNCER = f"{DOCS_BASE_URL}/syncer/what-is"
GH_DISCUSS = "https://github.com/thoughtspot/cs_tools/discussions/55"
