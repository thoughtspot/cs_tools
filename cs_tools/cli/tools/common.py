from typing import Any, Dict, List, Tuple
import logging
import pathlib

from click.exceptions import BadParameter
import click
import httpx

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


def split_args_from_opts(extra_args: List[str]) -> Tuple[List[str], Dict[str, Any], List[str]]:
    """
    """
    args = []
    flag = []
    opts = {}
    skip = False
    last = len(extra_args) - 1

    for i, arg in enumerate(extra_args[:]):
        if skip:
            skip = False
        elif arg.startswith("--"):
            name = arg[2:]

            if i != last and not extra_args[i + 1].startswith("--"):
                opts[name] = extra_args[i + 1]
                skip = True
            else:
                flag.append(name)
        else:
            args.append(arg)

    return args, opts, flag


import contextlib
import inspect
from cs_tools.const import APP_DIR
@contextlib.contextmanager
def thoughtspot(ctx: click.Context, *, login: bool = True) -> ThoughtSpot:
    """
    """
    if hasattr(ctx.obj, "thoughtspot"):
        return ctx.obj.thoughtspot

    args, options, flags = split_args_from_opts(ctx.args)

    config = options.pop("config", TSConfig.check_for_default())

    # click interpreted `--config NAME` as an Argument value because the argument itself
    # was missing.
    for name, value in ctx.params.items():
        if value == "--config":
            ctx.fail(f"Missing argument '{name.upper()}'")

    if config is None:
        raise BadParameter("no --config specified", ctx=ctx) from None

    sig = inspect.signature(TSConfig.from_toml).parameters
    extra = set(options).difference(sig)

    if extra:
        extra_args = " ".join(f"--{k} {v}" for k, v in options.items() if k in extra)
        ctx.fail(f"Got unexpected extra arguments ({extra_args})")

    if args:
        log.warning(f"[yellow]Ignoring extra arguments ({' '.join(args)})")

    if flags:
        log.warning(f"[yellow]Ignoring extra flags ({' '.join(flags)})")

    cfg = TSConfig.from_toml(APP_DIR / f'cluster-cfg_{config}.toml', **options)
    ctx.obj.thoughtspot = ThoughtSpot(cfg)

    if login:
        print('logging in')
        ctx.obj.thoughtspot.login()

    yield ctx.obj.thoughtspot

    try:
        print('logging out')
        ctx.obj.thoughtspot.logout()
    except httpx.HTTPStatusError:
        pass
