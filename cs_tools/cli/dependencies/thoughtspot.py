from __future__ import annotations

from types import TracebackType
import collections
import logging

from typer.core import TyperOption
import click
import httpx
import typer

from cs_tools import utils
from cs_tools.cli.dependencies.base import Dependency
from cs_tools.settings import (
    CSToolsConfig,
    _meta_config as meta,
)
from cs_tools.thoughtspot import ThoughtSpot
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
    param_decls=["--verbose", "-v"],
    default=0,
    metavar="",
    show_default=False,
    count=True,
    help="verbosity level of log files, can be included multiple times",
    rich_help_panel="[ThoughtSpot Config Overrides]",
)


class DThoughtSpot(Dependency):
    """Inject ThoughtSpot in commands."""

    login: bool = True

    def __call__(self, ctx: typer.Context):
        return getattr(ctx.obj, "thoughtspot", self)

    def _process_leftover_options(self) -> None:
        """Perform parsing of extra args."""
        ctx = click.get_current_context()

        # DEV NOTE: @boonhapus, 2024/04/03
        # context.args.... list[str], the leftover arguments
        # context.params.. dict[str, Any], parameter names to parsed values. params with expose_value=False arn't stored
        #
        # Basiclly, we want to take the args, check if `--config` is in them and add it to .params
        #

        extra: list[str] = []
        unrecognized = collections.deque(ctx.args)

        while unrecognized:
            argument = unrecognized.popleft()

            # THIS IS TRULY SOME EXTRA INPUT.
            if not argument.startswith("--"):
                extra.append(argument)
                continue

            argument = argument.removeprefix("--")

            try:
                next_argument = unrecognized.popleft()

            # THIS ARGUMENT IS A FLAG VALUE, AND IT'S SPECIFIED (aka True)
            except IndexError:
                ctx.params[argument] = True
                continue

            # THIS ARGUMENT IS A FLAG VALUE, AND IT'S SPECIFIED (aka True)
            if next_argument.startswith("--"):
                ctx.params[argument] = True
                unrecognized.appendleft(next_argument)

            # THIS ARGUMENT IS A FLAG VALUE
            else:
                ctx.params[argument] = next_argument

        ctx.args = extra

    def __enter__(self):
        self._send_analytics_in_background()
        self._process_leftover_options()

        ctx = click.get_current_context()

        if (config := ctx.params.pop("config", meta.default_config_name)) is None:
            ctx.fail("Missing [b blue]--config[/], and no [b green]default config[/] is set")

        if ctx.args:
            log.warning(f"[b yellow]Ignoring extra arguments ({' '.join(ctx.args)})")

        command_params = [p.name for p in ctx.command.params]
        overrides = {k: ctx.params.pop(k) for k in ctx.params.copy() if k not in command_params}

        log.debug(f"Command Overrides: {' '.join(overrides)}")

        cfg = CSToolsConfig.from_name(config, **overrides, automigrate=True)

        if cfg.verbose:
            root = logging.getLogger()
            term = next(h for h in root.handlers if getattr(h, "name", h.__class__.__name__) == "to_console")
            term.setLevel(5)

        ctx.obj.thoughtspot = ThoughtSpot(cfg, auto_login=self.login)

    def _send_analytics_in_background(self) -> None:
        """Send analyics in the background."""
        if meta.analytics.is_opted_in is not True or meta.environment.is_dev:
            return

        # AVOID CIRCULAR IMPORTS WITH cli.ux
        from cs_tools.cli import _analytics

        background = utils.ExceptedThread(target=_analytics.maybe_send_analytics_data)
        background.start()

    def __exit__(self, exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType) -> None:
        ctx = click.get_current_context()

        try:
            ctx.obj.thoughtspot.logout()
        except httpx.HTTPStatusError:
            pass


thoughtspot = DThoughtSpot(parameters=[CONFIG_OPT, TEMP_DIR_OPT, VERBOSE_OPT])
thoughtspot_nologin = DThoughtSpot(login=False, parameters=[CONFIG_OPT, TEMP_DIR_OPT, VERBOSE_OPT])
