from typing import List, Dict, Any
import logging
import pathlib
import csv

import click

from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig, _meta_config


log = logging.getLogger(__name__)


def setup_thoughtspot(
    ctx: click.Context,
    *,
    config: str = 'CHECK_FOR_DEFAULT',
    verbose: bool = None,
    temp_dir: pathlib.Path = None
) -> ThoughtSpot:
    """
    Returns the ThoughtSpot object.
    """
    if config == 'CHECK_FOR_DEFAULT':
        config = _meta_config()['default']['config']
        try:
            config = _meta_config()['default']['config']
        except KeyError:
            raise click.exceptions.BadParameter('no --config specified', ctx=ctx) from None

    if not hasattr(ctx.obj, 'thoughtspot'):
        cfg = TSConfig.from_command(config, verbose=verbose, temp_dir=temp_dir)
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
