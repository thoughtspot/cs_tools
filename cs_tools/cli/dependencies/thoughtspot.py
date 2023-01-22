from dataclasses import dataclass
from typing import Tuple, List, Dict, Any
import logging
import inspect

from typer.core import TyperOption
import typer
import httpx
import click

from cs_tools.cli.dependencies.base import Dependency
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import _meta_config, CSToolsConfig
from cs_tools.const import APP_DIR

meta = _meta_config.load()
log = logging.getLogger(__name__)


CONFIG_OPT = TyperOption(
    param_decls=["--config"],
    help=f"config file identifier{' (default is set)' if meta.default_config_name is None else ''}",
    metavar=f"{meta.default_config_name or 'NAME'}",
    required=meta.default_config_name is None,
    rich_help_panel="[ThoughtSpot Config Overrides]",
)

TEMP_DIR_OPT = TyperOption(
    param_decls=["--temp_dir"],
    default=APP_DIR.as_posix(),
    help="location on disk to save temporary files",
    show_default=False,
    metavar="PATH",
    rich_help_panel="[ThoughtSpot Config Overrides]",
)

VERBOSE_OPT = TyperOption(
    param_decls=["--verbose"],
    help="enable verbose logging",
    show_default=False,
    is_flag=True,
    rich_help_panel="[ThoughtSpot Config Overrides]",
)


def split_args_from_opts(extra_args: List[str]) -> Tuple[List[str], Dict[str, Any], List[str]]:
    """ """
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


@dataclass
class DThoughtSpot(Dependency):
    login: bool = True

    def __call__(self, ctx: typer.Context):
        if hasattr(ctx.obj, "thoughtspot"):
            return ctx.obj.thoughtspot
        return self

    def __enter__(self):
        ctx = click.get_current_context()
        args, options, flags = split_args_from_opts(ctx.args)

        config = options.pop("config", CSToolsConfig.get_default_config_name())

        # click interpreted `--config NAME` as an Argument value because the argument itself
        # was missing.
        for name, value in ctx.params.items():
            if value == "--config":
                ctx.fail(f"Missing argument '{name.upper()}'")

        if config is None:
            ctx.fail("no environment specified for --config")

        sig = inspect.signature(CSToolsConfig.from_toml).parameters
        extra = set(options).difference(sig)
        flags = set(flags).difference(sig)

        if extra:
            extra_args = " ".join(f"--{k} {v}" for k, v in options.items() if k in extra)
            ctx.fail(f"Got unexpected extra arguments ({extra_args})")

        if args:
            log.warning(f"[b yellow]Ignoring extra arguments ({' '.join(args)})")

        if flags:
            log.warning(f"[b yellow]Ignoring extra flags ({' '.join(flags)})")

        cfg = CSToolsConfig.from_toml(APP_DIR / f"cluster-cfg_{config}.toml", **options)
        ctx.obj.thoughtspot = ThoughtSpot(cfg)

        if self.login:
            ctx.obj.thoughtspot.login()

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        ctx = click.get_current_context()

        try:
            ctx.obj.thoughtspot.logout()
        except httpx.HTTPStatusError:
            pass


thoughtspot = DThoughtSpot(parameters=[CONFIG_OPT, TEMP_DIR_OPT, VERBOSE_OPT])
thoughtspot_nologin = DThoughtSpot(login=False, parameters=[CONFIG_OPT, TEMP_DIR_OPT, VERBOSE_OPT])
