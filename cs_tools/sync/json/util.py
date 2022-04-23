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
    data : Dict[str, RECORDS_FORMAT]
    """
    if fp.stat().st_size == 0:
        return None

    with fp.open('r') as j:
        data = json.load(j)

    # file with a single table stores records directly
    if isinstance(data, list):
        data = {fp.name: data}

    return data
