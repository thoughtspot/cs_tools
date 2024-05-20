from __future__ import annotations

from typing import Any
import datetime as dt
import json


def clean_datetime(o: Any) -> str:
    """Convert the datatime into a string."""
    if isinstance(o, dt.datetime):
        return o.strftime("%Y-%m-%dT%H:%M:%S.%f")
    return o


def clean_for_bq(data: list[dict[str, Any]]) -> list[dict[str, str]]:
    """
    Round-trip from JSON to sanitize.

    BigQuery API has a few requirements
    - only accepts strings
    - default serialization of DATETIME format includes timezone, BQ complains

    Further reading:
      https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types#datetime_type

    Parameters
    ----------
    data : List[Dict[str, Any]]
      objects to clean, values can be in any format

    Returns
    -------
    cleaned : List[Dict[str, str]]
    """
    return json.loads(json.dumps(data, default=clean_datetime))
