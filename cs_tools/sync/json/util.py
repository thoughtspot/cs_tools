from typing import Any, Dict
import pathlib
import json


def read_from_possibly_empty(fp: pathlib.Path) -> Dict[str, Any]:
    """
    Read a file into memory, casting to dict if empty.

    Parameters
    ----------
    fp : pathlib.Path
      file to read

    Returns
    -------
    data : Dict[str, Any]
    """
    if fp.stat().st_size == 0:
        return {}

    with fp.open('r') as j:
        return json.load(j)
