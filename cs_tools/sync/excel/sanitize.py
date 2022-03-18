from typing import Any, Dict, List
import datetime as dt
import json

from cs_tools.const import FMT_TSLOAD_DATETIME


class MaybeDateTimeEncoder(json.JSONEncoder):
    """
    Include a check for datetime.datetime.
    """
    def default(self, o: Any):
        if isinstance(o, dt.datetime):
            return o.strftime(FMT_TSLOAD_DATETIME)

        return super().default(self, o)


def clean_for_excel(data: List[Dict[str, Any]]) -> List[List[str]]:
    """
    Round-trip from JSON to sanitize.

    Excel has only accepts strings

    Parameters
    ----------
    data : List[Dict[str, Any]]
      objects to clean, values can be in any format

    Returns
    -------
    cleaned : List[List[str]]
    """
    # round-trip to sanitize because gspread only accepts strings
    d = [list(_.values()) for _ in data]
    return json.loads(json.dumps(d, cls=MaybeDateTimeEncoder, default=str))
