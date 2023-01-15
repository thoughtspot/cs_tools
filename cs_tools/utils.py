from typing import Optional, Callable, Any
from base64 import urlsafe_b64encode as b64e
from base64 import urlsafe_b64decode as b64d
import collections.abc
import zlib


def chunks(iter_, *, n: int) -> iter:
    """
    Yield successive n-sized chunks from lst.
    """
    for i in range(0, len(iter_), n):
        yield iter_[i : i + n]


def deep_update(old: dict, new: dict, *, ignore: Any = None) -> dict:
    """
    Update existing dictionary with new data.

    The operation dict1.update(dict2) will overwrite data in dict1 if it
    is a multilevel dictionary with overlapping keys in dict2. This
    recursive function solves that specific problem.

    Parameters
    ----------
    old : dict
      old dictionary to update

    new : dict
      new dictionary to pull values from

    ignore : anything [default: None]
      ignore values like <ignore>

    Returns
    -------
    updated : dict
      old dictionary updated with new's values
    """
    for k, v in new.items():
        if v is ignore or str(v) == str(ignore):
            continue

        if isinstance(v, collections.abc.Mapping):
            v = deep_update(old.get(k, {}), v, ignore=ignore)

        if old is None:
            old = {}

        old[k] = v

    return old


def obscure(data: bytes) -> bytes:
    """
    Encode data to obscure its text.

    This is security by obfuscation.
    """
    if data is None:
        return

    if isinstance(data, str):
        data = str.encode(data)

    return b64e(zlib.compress(data, 9))


def reveal(obscured: bytes) -> bytes:
    """
    Decode obscured data to reveal its text.

    This is security by obfuscation.
    """
    if obscured is None:
        return

    return zlib.decompress(b64d(obscured))


def find(predicate: Callable[[Any], [bool]], iterable: list[Any]) -> Any:
    """
    Return the first element in the sequence that meets the predicate.
    """
    for element in iterable:
        if predicate(element):
            return element

    return None


class State:
    """
    An object that can be used to store arbitrary state.
    """

    _state: dict[str, Any]

    def __init__(self, state: Optional[dict[str, Any]] = None):
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
            raise AttributeError(f"'{cls_name}' object has no attribute '{key}'")

    def __delattr__(self, key: Any) -> None:
        del self._state[key]
