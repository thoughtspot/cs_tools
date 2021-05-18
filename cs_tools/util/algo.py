from typing import Iterable
import collections.abc


def dedupe(iterable: Iterable) -> Iterable:
    """
    Removes duplicates.

    In python 3.6+, this algorithm preserves order of the underlying
    iterable.
    """
    return iter(dict.fromkeys(iterable))


def deep_update(old: dict, new: dict, *, ignore_none: bool=False) -> dict:
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

    ignore_none : bool [default: False]
      whether or not to ignore None values

    Returns
    -------
    updated : dict
      old dictionary updated with new's values
    """
    for k, v in new.items():
        if v is None and ignore_none:
            continue

        if isinstance(v, collections.abc.Mapping):
            v = deep_update(old.get(k, {}), v, ignore_none=ignore_none)

        old[k] = v

    return old
