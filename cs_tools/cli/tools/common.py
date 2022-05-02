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
