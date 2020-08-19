"""
Utilities for when working with the Swagger API.
"""
from typing import Iterable

from thoughtspot.util.algo import dedupe


def to_array(iterable: Iterable[str]) -> str:
    """
    Converts an iterable to a stringified array.

    >>> my_iter = ['guid1', 'guid2', 'guid3']
    >>> to_array(my_iter)
    '[guid1, guid2, guid3]'
    """
    return repr(list(dedupe(iterable))).replace("'", '')
