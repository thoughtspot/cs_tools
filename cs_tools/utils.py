from __future__ import annotations

from base64 import (
    urlsafe_b64decode as b64d,
    urlsafe_b64encode as b64e,
)
from collections.abc import Awaitable, Coroutine, Generator, Iterable
from contextvars import Context
from typing import Any, TypeVar
import asyncio
import datetime as dt
import getpass
import importlib
import itertools as it
import os
import pathlib
import site
import zlib

_T = TypeVar("_T")
_EVENT_LOOP: asyncio.AbstractEventLoop | None = None


def get_event_loop() -> asyncio.AbstractEventLoop:
    """Fetch an event loop."""
    # DEV NOTE: @boonhapus, 2024/11/24
    # IF WE WERE TO SWITCH TO thoughtspot.ThoughtSpot ACTING AS A GLOBAL ENTRYPOINT THEN
    # THIS FUNCTION WOULD BE NO LONGER NEEDED, AND WE COULD USE asyncio.run() INSTEAD.
    global _EVENT_LOOP

    # RETURN THE EVENT LOOP IF IT'S ALREADY BEEN SET FOR THE PROCESS.
    if _EVENT_LOOP is not None:
        return _EVENT_LOOP

    try:
        loop = asyncio.get_running_loop()

    except RuntimeError:
        loop = asyncio.new_event_loop()

        # SET THE EVENT LOOP ON THE THREAD.
        asyncio.set_event_loop(loop)

        # SET THE EVENT LOOP FOR THE PROCESS.
        _EVENT_LOOP = loop

    return loop


def run_sync(coro: Awaitable) -> Any:
    """Run a coroutine synchronously."""
    return get_event_loop().run_until_complete(coro)


class BoundedTaskGroup(asyncio.TaskGroup):
    """An asyncio.TaskGroup that implements backpressure."""

    def __init__(self, max_concurrent: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(value=max_concurrent)

    def create_task(self, coro: Coroutine, *, name: str | None = None, context: Context | None = None) -> asyncio.Task:
        """See: https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup.create_task"""

        async def with_backpressure() -> Any:
            async with self._semaphore:
                return await coro

        return super().create_task(coro=with_backpressure(), name=name, context=context)


def batched(iterable: Iterable[_T], *, n: int) -> Generator[Iterable[_T], None, None]:
    """Yield successive n-sized chunks from list."""
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")

    iterable = iter(iterable)

    while batch := tuple(it.islice(iterable, n)):
        yield batch


def determine_editable_install() -> bool:
    """Determine if the current CS Tools context is an editable install."""
    if "FAKE_EDITABLE" in os.environ:
        return True

    for directory in site.getsitepackages():
        try:
            site_directory = pathlib.Path(directory)

            for path in site_directory.iterdir():
                if not path.is_file():
                    continue

                if "__editable__.cs_tools" in path.as_posix():
                    return True

        # not all distros will bundle python the same (eg. ubuntu-slim)
        except FileNotFoundError:
            continue

    return False


def obscure(data: bytes) -> bytes:
    """
    Encode data to obscure its text.

    This is security by obfuscation.
    """
    if data is None:
        return

    if isinstance(data, str):
        data = str.encode(data)

    return b64e(zlib.compress(data, level=9))


def reveal(obscured: bytes) -> bytes:
    """
    Decode obscured data to reveal its text.

    This is security by obfuscation.
    """
    if obscured is None:
        return
    return zlib.decompress(b64d(obscured))


def anonymize(text: str, *, anonymizer: str = " {anonymous} ") -> str:
    """Replace text with an anonymous value."""
    text = text.replace(getpass.getuser(), anonymizer)
    return text


class GlobalState:
    """An object that can be used to store arbitrary state."""

    _state: dict[str, Any]

    def __init__(self, state: dict[str, Any] | None = None):
        if state is None:
            state = {}

        super().__setattr__("_state", state)

    def __setattr__(self, key: Any, value: Any) -> None:
        self._state[key] = value

    def __getattr__(self, key: Any) -> Any:
        try:
            return self._state[key]
        except KeyError:
            cls_name = self.__class__.__name__
            raise AttributeError(f"'{cls_name}' object has no attribute '{key}'") from None

    def __delattr__(self, key: Any) -> None:
        del self._state[key]


def get_package_directory(package_name: str) -> pathlib.Path | None:
    """Get the path to the package directory."""
    try:
        module = importlib.import_module(package_name)
        assert module.__spec__ is not None
        assert module.__spec__.origin is not None

    except (ModuleNotFoundError, AssertionError):
        return None

    return pathlib.Path(module.__spec__.origin).parent


def timedelta_strftime(timedelta: dt.timedelta, *, sep: str = " ") -> str:
    """Convert a timedelta to an fstring HHH:MM:SS."""
    total_seconds = int(timedelta.total_seconds())
    H, r = divmod(total_seconds, 3600)
    M, S = divmod(r, 60)
    return f"{H: 3d}h{sep}{M:02d}m{sep}{S:02d}s"
