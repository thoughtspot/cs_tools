"""
Do not rely on these. This is a legacy implementation of global context.

It will be refactored out.
"""

import pathlib


PACKAGE_DIR = pathlib.Path(__file__).parent

# ISO datetime format
FMT_TSLOAD_DATE = "%Y-%m-%d"
FMT_TSLOAD_TIME = "%H:%M:%S"
FMT_TSLOAD_DATETIME = f"{FMT_TSLOAD_DATE} {FMT_TSLOAD_TIME}"
FMT_TSLOAD_TRUE_FALSE = "True_False"
