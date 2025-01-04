import sys


if sys.version_info >= (3, 10):  # AVAILABLE_IN_PY310
    # https://docs.python.org/3/library/typing.html#typing.TypeAlias
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

if sys.version_info >= (3, 11):  # AVAILABLE_IN_PY311
    # https://docs.python.org/3/library/exceptions.html#exception-groups
    ExceptionGroup = ExceptionGroup

    # https://docs.python.org/3/library/typing.html#typing.Self
    from typing import Self

    # https://docs.python.org/3/library/typing.html#typing.TypedDict
    # for..  typing.Required and typing.NotRequired support (PEP 655)
    from typing import TypedDict

    # https://docs.python.org/3/library/enum.html#enum.StrEnum
    from enum import StrEnum

    # https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup
    from asyncio import TaskGroup
else:
    from typing_extensions import Self
    from typing_extensions import TypedDict
    from exceptiongroup import ExceptionGroup
    from strenum import StrEnum
    from taskgroup import TaskGroup
