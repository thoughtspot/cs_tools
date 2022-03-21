from typing import List, Dict, Any
import logging
import pathlib
import csv

import click

from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig


log = logging.getLogger(__name__)


def setup_thoughtspot(config_name: str, *, ctx: click.Context) -> ThoughtSpot:
    """
    Returns the ThoughtSpot object.
    """
    if not hasattr(ctx.obj, 'thoughtspot'):
        cfg = TSConfig.from_config_name(config_name)
        ctx.obj.thoughtspot = ThoughtSpot(cfg)

    return ctx.obj.thoughtspot


def to_csv(
    data: List[Dict[str, Any]],
    fp: pathlib.Path,
    *,
    mode: str = 'w',
    sep: str = '|',
    header: bool = False
):
    """
    Write data to CSV.

    Data must be in record format.. [{column -> value}, ..., {column -> value}]
    """
    header = header or not fp.exists()

    with fp.open(mode=mode, encoding='utf-8', newline='') as c:
        writer = csv.DictWriter(c, data[0].keys(), delimiter=sep)

        if header:
            writer.writeheader()

        writer.writerows(data)
