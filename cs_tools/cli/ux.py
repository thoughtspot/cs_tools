from __future__ import annotations

from collections.abc import Generator
from typing import Any, Callable, Optional, cast
import asyncio
import contextlib
import functools as ft
import inspect
import logging

from rich import theme
from rich.console import Console
from typer.models import CommandFunctionType as CommandFnType
import typer

from cs_tools import utils

log = logging.getLogger(__name__)

# fmt: off
_TS_RED  = "#fe4870"
_TS_BLUE = "#0567fa"
_TS_PURPLE = "#8d63f5"
_TS_GREEN = "#4ab565"
_TS_YELLOW = "#fcc839"
# fmt: on

CS_TOOLS_THEME = theme.Theme(
    {
        "fg-primary": "white",
        "fg-secondary": _TS_PURPLE,
        "fg-success": _TS_GREEN,
        "fg-warn": _TS_YELLOW,
        "fg-error": _TS_RED,
        "bg-primary": "b grey50",
    },
    inherit=True,
)

RICH_CONSOLE = rich_console = Console(theme=CS_TOOLS_THEME)


@contextlib.contextmanager
def _pause_live_for_debugging() -> Generator[None, None, None]:
    """Pause live updates for debugging."""
    if RICH_CONSOLE._live is not None:
        RICH_CONSOLE._live.stop()

    yield

    if RICH_CONSOLE._live is not None:
        RICH_CONSOLE.clear()
        RICH_CONSOLE._live.start(refresh=True)


class AsyncTyper(typer.Typer):
    """Allow Typer to run on async functions."""

    def __init__(self, **passthru):
        ctx_settings = passthru.pop("context_settings", None) or {}
        ctx_settings["help_option_names"] = ["--help", "-h"]
        ctx_settings["obj"] = utils.GlobalState()
        ctx_settings["max_content_width"] = RICH_CONSOLE.width
        ctx_settings["token_normalize_func"] = str.casefold

        cmd_settings = {"context_settings": ctx_settings, "add_completion": False, "rich_markup_mode": "rich"}

        super().__init__(**passthru, no_args_is_help=True, **cmd_settings)  # type: ignore

    @staticmethod
    def maybe_run_async(decorator: Callable[[CommandFnType], CommandFnType], fn: CommandFnType) -> CommandFnType:
        """Optionally wrap a typer command function in an async context."""
        # DEV NOTE: @boonhapus, 2024-09-24
        # Why loop.stop() instead of asyncio.run()? Mostly to handle KeyboardInterrupt.
        #
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if inspect.iscoroutinefunction(fn):

            @ft.wraps(fn)
            def runner(*args: Any, **kwargs: Any) -> Any:
                try:
                    coro = fn(*args, **kwargs)
                    return loop.run_until_complete(coro)
                except KeyboardInterrupt:
                    log.critical("KI encountered.. stopping event loop")
                finally:
                    loop.stop()

            return decorator(cast(CommandFnType, runner))

        return decorator(fn)

    def callback(self, **typer_options: Any) -> Callable[[CommandFnType], CommandFnType]:
        """See: https://typer.tiangolo.com/tutorial/commands/callback/"""
        decorator = super().callback(**typer_options)
        return lambda f: self.maybe_run_async(decorator, f)

    def command(self, name: Optional[str] = None, **typer_options: Any) -> Callable[[CommandFnType], CommandFnType]:
        """See: https://typer.tiangolo.com/tutorial/commands/"""
        decorator = super().command(name=name, **typer_options)
        return lambda f: self.maybe_run_async(decorator, f)


CSToolsApp = AsyncTyper
CSToolsGroup = typer.core.TyperGroup
CSToolsCommand = typer.core.TyperCommand
