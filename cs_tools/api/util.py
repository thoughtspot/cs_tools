"""
Utilities for when working with the Swagger API.
"""
from typing import Any, Dict, Iterable
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
    if not iterable:
        return None

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


def filter_none(request_parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter None values out of request params.

    Why? If you supply an incorrect or unexpected value to ThoughtSpot API parameters,
    then the endpoint will silently ignore all parameters. Empty values included. None
    is not a valid parameter value, so we can confidently use it as a sentinel.

    Parameters
    ----------
    request_parameters : Dict[str, Any]
      keywords passed to http.request
    """
    kw = {}

    for k, v in request_parameters.items():
        if isinstance(v, dict):
            v = filter_none(v)
        
        if v is not None:
            kw[k] = v

    return kw


def before_version(version: str, compare_to_version: str) -> bool:
    """
    Returns True of the version is earlier than the comparison version.  Only the first two parts are examined.
    It's assumed that there are always two parts.
    Examples:
        8.2 is before 8.9
        8.2 is not before 8.2.3
    """
    v_major, v_minor, *other = version.split(".")
    ct_major, ct_minor, *other = compare_to_version.split(".")

    return v_major < ct_major or (v_major == ct_major and v_minor < ct_minor)
