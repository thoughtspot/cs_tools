from typing import List, Dict, Any
import datetime as dt
import json

from .const import BIG_QUERY_DATETIME_FORMAT


def clean_datetime(o: Any) -> str:
    """ """
    if isinstance(o, dt.datetime):
        return o.strftime(BIG_QUERY_DATETIME_FORMAT)
    return o


def clean_for_bq(data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
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
