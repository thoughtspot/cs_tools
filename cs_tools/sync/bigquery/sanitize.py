from typing import Any, Dict, List
import datetime as dt
import json

from .const import BIG_QUERY_DATETIME_FORMAT


class MaybeDateTimeEncoder(json.JSONEncoder):
    """
    Include a check for datetime.datetime.
    """
    def default(self, o: Any):
        if isinstance(o, dt.datetime):
            return o.strftime(BIG_QUERY_DATETIME_FORMAT)

        return super().default(self, o)


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
    return json.loads(json.dumps(data, cls=MaybeDateTimeEncoder, default=str))
