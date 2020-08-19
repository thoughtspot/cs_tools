from typing import Iterable


def dedupe(iterable: Iterable) -> Iterable:
    """
    Removes duplicates.

    In python 3.6+, this algorithm preserves order of the underlying
    iterable.
    """
    return iter(dict.fromkeys(iterable))
