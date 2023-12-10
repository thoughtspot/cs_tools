from __future__ import annotations

from typing import Any
import datetime as dt
import json

import sqlmodel

from cs_tools.const import FMT_TSLOAD_DATETIME


def clean_datetime(o: Any) -> str:
    """ """
    if isinstance(o, dt.datetime):
        return o.strftime(FMT_TSLOAD_DATETIME)
    if isinstance(o, sqlmodel.SQLModel):
        return o.dict()
    return json.dumps(o)


def clean_for_falcon(data: list[dict[str, Any]]) -> list[list[str]]:
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
