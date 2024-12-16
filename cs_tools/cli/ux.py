from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING, Any, Callable, Optional
import contextlib
import logging
import sys

from rich import theme
from rich.console import Console
import typer

from cs_tools import __project__, utils
from cs_tools.cli.types import SyncerProtocolType

if TYPE_CHECKING:
    import click

log = logging.getLogger(__name__)

# fmt: off
_TS_RED  = "#fe4870"
_TS_BLUE = "#0567fa"
_TS_PURPLE = "#8d63f5"
_TS_GREEN = "#4ab565"
_TS_YELLOW = "#fcc839"
# fmt: on

RICH_CONSOLE = rich_console = Console(
    theme=theme.Theme(
        {
            "fg-primary": "white",
            "fg-secondary": _TS_PURPLE,
            "fg-success": _TS_GREEN,
            "fg-warn": _TS_YELLOW,
            "fg-error": _TS_RED,
            "bg-primary": "b grey50",
        },
    ),
)


@contextlib.contextmanager
def _pause_live_for_debugging() -> Generator[None, None, None]:
    """Pause live updates for debugging."""
    if RICH_CONSOLE._live is not None:
        RICH_CONSOLE._live.stop()

    yield

    if RICH_CONSOLE._live is not None:
        RICH_CONSOLE.clear()
        RICH_CONSOLE._live.start(refresh=True)


class CSToolsCommand(typer.core.TyperCommand):
    """CSTools Commands can have dependencies."""

    def __init__(self, **passthru):
        # We need these to forward options to the dependencies
        ctx_settings = passthru.pop("context_settings") or {}
        ctx_settings["allow_extra_args"] = True
        ctx_settings["ignore_unknown_options"] = True
        super().__init__(**passthru, context_settings=ctx_settings)
        self.dependencies: Callable[[click.Context], Any] = getattr(self.callback, "__cs_tools_dependencies__", [])

    def invoke(self, ctx: typer.Context) -> Any:
        """Hi-jack command execution to fire off dependencies."""
        with contextlib.ExitStack() as stack:
            for dependency in self.dependencies:
                stack.enter_context(dependency(ctx))

            r = ctx.invoke(self.callback, **ctx.params)

        return r

    def _augment_help_text(self, ctx: typer.Context, *, seen_params: list[click.Parameter]) -> list[click.Parameter]:
        """
        Inject Dependency parameters and help text.

        This action is performed for the --help commands only.
        """
        # no help command was sent, pass back what we saw..
        if not set(sys.argv[1:]).intersection(ctx.help_option_names):
            return seen_params

        # inject dependency's Parameters
        for dependency in self.dependencies:
            seen_params.extend([p for p in dependency.parameters if p not in seen_params])

        # add syncer documentation page help text
        if any(isinstance(p.type, SyncerProtocolType) for p in seen_params):
            syncer = f" :floppy_disk: [cyan][link={__project__.__docs__}/syncer/what-is/]How do I use a Syncer?[/][/]"

            if self.epilog is None:
                self.epilog = ""

            if syncer not in self.epilog:
                self.epilog += syncer

        return seen_params

    def get_params(self, ctx: typer.Context) -> list[click.Parameter]:
        """Hi-jack for dependency help-text augmentations."""
        rv = super().get_params(ctx)
        rv = self._augment_help_text(ctx, seen_params=rv)
        return rv


class CSToolsGroup(typer.core.TyperGroup):
    """CSTools Groups should always recurse, and use CSToolsCommand."""

    command_class = CSToolsCommand
    group_class = type

    def list_commands(self, ctx: typer.Context) -> list[str]:  # noqa: ARG002
        """Override so we don't sort alphabetically."""
        return list(self.commands)


class CSToolsApp(typer.Typer):
    def __init__(self, **passthru):
        # We need to enforce these options for all Apps
        passthru["cls"] = CSToolsGroup
        passthru["rich_markup_mode"] = "rich"
        passthru["no_args_is_help"] = True

        ctx_settings = passthru.pop("context_settings", None) or {}
        ctx_settings["help_option_names"] = ["--help", "-h"]
        ctx_settings["obj"] = utils.GlobalState()
        ctx_settings["max_content_width"] = RICH_CONSOLE.width
        ctx_settings["token_normalize_func"] = lambda x: x.casefold()
        super().__init__(**passthru, context_settings=ctx_settings)

    def command(
        self,
        name: Optional[str] = None,
        *,
        dependencies: Optional[list[Callable]] = None,
        # better typer defaults
        cls: Optional[CSToolsCommand] = CSToolsCommand,
        no_args_is_help: bool = True,
        **passthru,
    ):
        """Hi-jack to store dependencies."""

        def decorator(f: Callable):
            if not hasattr(f, "__cs_tools_dependencies__"):
                f.__cs_tools_dependencies__ = []

            if dependencies is not None:
                f.__cs_tools_dependencies__.extend(dependencies)

            info = typer.models.CommandInfo(name=name, cls=cls, callback=f, no_args_is_help=no_args_is_help, **passthru)
            self.registered_commands.append(info)
            return f

        return decorator
