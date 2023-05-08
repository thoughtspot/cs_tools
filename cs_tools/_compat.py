import sys

if sys.version_info < (3, 8):
    from typing_extensions import TypedDict, Literal
else:
    # AVAILABLE IN PYTHON 3.8
    from typing import TypedDict, Literal


if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
    # AVAILABLE IN PYTHON 3.11
    from enum import StrEnum
