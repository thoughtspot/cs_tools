import logging
import pathlib

from click.exceptions import BadParameter
import click

from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig, _meta_config


log = logging.getLogger(__name__)


def setup_thoughtspot(
    ctx: click.Context,
    *,
    config: str = 'CHECK_FOR_DEFAULT',
    verbose: bool = None,
    temp_dir: pathlib.Path = None,
    login: bool = True
) -> ThoughtSpot:
    """
    Returns the ThoughtSpot object.
    """
    if hasattr(ctx.obj, 'thoughtspot'):
        return ctx.obj.thoughtspot

    if config == 'CHECK_FOR_DEFAULT':
        try:
            config = _meta_config()['default']['config']
        except KeyError:
            raise BadParameter('no --config specified', ctx=ctx) from None

    cfg = TSConfig.from_command(config, verbose=verbose, temp_dir=temp_dir)
    ctx.obj.thoughtspot = ts = ThoughtSpot(cfg)

    if login:
        ts.login()

    return ts


def teardown_thoughtspot(ctx: click.Context):
    """
    Destroys the ThoughtSpot object.
    """
    if hasattr(ctx.obj, 'thoughtspot'):
        ctx.obj.thoughtspot.logout()
