from typing import Any, Dict, List, Tuple
import contextlib
import inspect
import logging

from typer.core import TyperOption
import click
import httpx

from cs_tools.cli.dependencies.base import Dependency
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig
from cs_tools.const import APP_DIR

log = logging.getLogger(__name__)


CONFIG_OPT = TyperOption(
    param_decls=["--config"],
    help="config file identifier",
    metavar="NAME",
    required=True,
    rich_help_panel="[ThoughtSpot Config Overrides]",
)

VERBOSE_OPT = TyperOption(
    param_decls=["--verbose"],
    help="enable verbose logging",
    show_default=False,
    is_flag=True,
    rich_help_panel="[ThoughtSpot Config Overrides]",
)

TEMP_DIR_OPT = TyperOption(
    param_decls=['--temp_dir'],
    default=APP_DIR.as_posix(),
    help='location on disk to save temporary files',
    show_default=False,
    metavar="PATH",
    rich_help_panel="[ThoughtSpot Config Overrides]",
)


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


@contextlib.contextmanager
def thoughtspot_cm(ctx: click.Context, *, login: bool = True) -> ThoughtSpot:
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
        ctx.fail("no environment specified for --config")

    sig = inspect.signature(TSConfig.from_toml).parameters
    extra = set(options).difference(sig)
    flags = set(flags).difference(sig)

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
        ctx.obj.thoughtspot.login()

    yield ctx.obj.thoughtspot

    try:
        ctx.obj.thoughtspot.logout()
    except httpx.HTTPStatusError:
        pass


thoughtspot = Dependency(callback=thoughtspot_cm, parameters=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT])
