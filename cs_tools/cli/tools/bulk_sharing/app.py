from __future__ import annotations

from typing import Literal

from textual_serve.server import Server
import typer

from cs_tools import _types
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.ux import AsyncTyper

from . import tui

app = AsyncTyper(
    name="bulk-sharing",
    help="""
    Scalably manage your table- and column-level security right in the browser.

    Setting up Column Level Security (especially on larger tables) can be time-consuming
    when done directly in the ThoughtSpot user interface. The web interface provided by
    this tool will allow you to quickly understand the current security settings for a
    given table across all columns, and as many groups as are in your platform. You may
    then set the appropriate security settings for those group-table combinations.
    """,
)


@app.callback()
def _noop(ctx: typer.Context) -> None:
    """Just here so that no_args_is_help=True works on a single-command Typer app."""


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def cls_ui(ctx: typer.Context, mode: Literal["web", "terminal"] = typer.Option("terminal")) ->_types.ExitCode:
    """Start the built-in webserver which runs the security management interface."""
    ts = ctx.obj.thoughtspot

    if mode == "web":
        server = Server(f"{tui.__file__} --config {ctx.obj.thoughtspot.config.name}")
        server.serve()
    else:
        ui = tui.ThoughtSpotSecurityApp(http=ts.api, ts_version=ts.session_context.thoughtspot.version)
        ui.run()

    return 0
