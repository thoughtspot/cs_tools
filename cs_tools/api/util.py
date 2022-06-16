"""
Utilities for when working with the Swagger API.
"""
from typing import Iterable
import uuid

from cs_tools.util import dedupe


def stringified_array(iterable: Iterable, *, unique: bool = True) -> str:
    """
    Convert an iterable into a string version.

    The REST v1 API accepts some parameters in the form of an array, but
    held as a string..

        https://my.thoughtspot.cloud
            ?type=LOGICAL_TABLE
            &subtypes=[WORKSHEET, USER_DEFINED]

    ..yet both requests and httpx see values in a list to `params` as
    multi-optioned paramaters..

        https://my.thoughtspot.cloud
            ?type=LOGICAL_TABLE
            &subtypes=WORKSHEET
            &subtypes=USER_DEFINED

    This function corrects this by simply converting the input into a
    comma-separated string.
    """
    if unique:
        iterable = dedupe(iterable)

    return '[' + ','.join(list(iterable)) + ']'


def is_valid_guid(to_test: str) -> bool:
    """
    Determine if value is a valid UUID.

    Parameters
    ----------
    to_test : str
        value to test
    """
    try:
        guid = uuid.UUID(to_test)
    except ValueError:
        return False
    return str(guid) == to_test
