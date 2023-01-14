from typing import Any, Dict, List
import datetime as dt
import json

from cs_tools.const import FMT_TSLOAD_DATETIME


def clean_datetime(o: Any) -> str:
    """ """
    if isinstance(o, dt.datetime):
        return o.strftime(FMT_TSLOAD_DATETIME)
    return o


def clean_for_falcon(data: List[Dict[str, Any]]) -> List[List[str]]:
    """
    Round-trip from JSON to sanitize.

    Falcon accepts datetimes in a specific format.

    Parameters
    ----------
    data : List[Dict[str, Any]]
      objects to clean, values can be in any format

    Returns
    -------
    cleaned : List[List[str]]
    """
    return json.loads(json.dumps(data, default=clean_datetime))
