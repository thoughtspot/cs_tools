import sys

if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
    # AVAILABLE IN PYTHON 3.11
    from enum import StrEnum
