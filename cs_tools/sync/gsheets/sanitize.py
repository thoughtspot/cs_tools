from typing import List, Dict, Any
import datetime as dt
import json

from .const import GOOGLE_SHEET_DATETIME_FORMAT


class MaybeDateTimeEncoder(json.JSONEncoder):
    """
    Include a check for datetime.datetime.
    """

    def default(self, o: Any):
        if isinstance(o, dt.datetime):
            return o.strftime(GOOGLE_SHEET_DATETIME_FORMAT)

        return super().default(self, o)


def clean_for_gsheets(data: List[Dict[str, Any]]) -> List[List[str]]:
    """
    Round-trip from JSON to sanitize.

    Google Sheets API has a few requirements
    - only accepts strings
    - won't accept in records-format

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
