from typing import List, Dict, Any
import json


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
    d = [list(_.values()) for _ in data]
    return json.loads(json.dumps(d, default=str))
