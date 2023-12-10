from __future__ import annotations

from typing import Any
import json


def clean_for_excel(data: list[dict[str, Any]]) -> list[list[str]]:
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
