import sys

# AVAILABLE IN PYTHON 3.8
from typing import TypedDict, Literal


# AVAILABLE IN PYTHON 3.9
from typing import Annotated


if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
    # AVAILABLE IN PYTHON 3.11
    from enum import StrEnum
