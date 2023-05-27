from dataclasses import dataclass
from typing import Tuple, List, Dict, Any
import logging
import inspect

from typer.core import TyperOption
import threading
import typer
import httpx
import click

from cs_tools.cli.dependencies.base import Dependency
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import _meta_config as meta, CSToolsConfig
from cs_tools.updater import cs_tools_venv

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
    default=cs_tools_venv.app_dir.as_posix(),
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

VERBOSE_OPT = TyperOption(
    param_decls=["--verbose", "-v"],
    default=0,
    metavar="",
    show_default=False,
    count=True,
    help="verbosity level of log files, can be included multiple times",
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

    def _send_analytics_in_background(self) -> None:
        DO_NOT_SEND_ANALYTICS = meta.analytics_opt_in in (None, False)

        if DO_NOT_SEND_ANALYTICS:
            return

        from cs_tools.cli import _analytics

        background = threading.Thread(target=_analytics.maybe_send_analytics_data)
        background.start()

    def __call__(self, ctx: typer.Context):
        if hasattr(ctx.obj, "thoughtspot"):
            return ctx.obj.thoughtspot
        return self

    def __enter__(self):
        self._send_analytics_in_background()

        ctx = click.get_current_context()
        args, options, flags = split_args_from_opts(ctx.args)

        config = options.pop("config", meta.default_config_name)

        # click interpreted `--config NAME` as an Argument value because the argument itself
        # was missing.
        for name, value in ctx.params.items():
            if value == "--config":
                ctx.fail(f"Missing argument '{name.upper()}'")

        if config is None:
            ctx.fail("Missing [b blue]--config[/], and no [b green]default config[/] is set")

        # add flags to options
        options = {**options, **{k: True for k in flags}}

        sig = inspect.signature(CSToolsConfig.from_toml).parameters
        extra = set(options).difference(sig)

        if extra:
            extra_args = " ".join(f"--{k} {v}" for k, v in options.items() if k in extra)
            ctx.fail(f"Got unexpected extra arguments ({extra_args})")

        if args:
            log.warning(f"[b yellow]Ignoring extra arguments ({' '.join(args)})")

        cfg = CSToolsConfig.from_toml(cs_tools_venv.app_dir / f"cluster-cfg_{config}.toml", **options)
        ctx.obj.thoughtspot = ThoughtSpot(cfg)

        if cfg.verbose:
            root_logger = logging.getLogger()
            to_file_handler = next((h for h in root_logger.handlers if h.name == "to_file"))
            to_file_handler.setLevel(5)
            root_logger.setLevel(5)

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
