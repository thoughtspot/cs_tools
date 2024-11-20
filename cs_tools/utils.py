from __future__ import annotations

from base64 import (
    urlsafe_b64decode as b64d,
    urlsafe_b64encode as b64e,
)
from collections.abc import Awaitable
from typing import Any
import asyncio
import getpass
import importlib
import os
import pathlib
import site
import zlib


def get_event_loop() -> asyncio.AbstractEventLoop:
    """Fetch an event loop."""
    try:
        loop = asyncio.get_running_loop()

    except RuntimeError:
        loop = asyncio.get_event_loop()

    return loop


def run_sync(coro: Awaitable) -> Any:
    """Run a coroutine synchronously."""
    return get_event_loop().run_until_complete(coro)


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
