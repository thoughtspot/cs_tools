from __future__ import annotations

from typing import Literal

from textual_serve.server import Server
import typer

from cs_tools import types
from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.ux import CSToolsApp

from . import tui

app = CSToolsApp(
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


@app.command(dependencies=[thoughtspot])
def cls_ui(ctx: typer.Context, mode: Literal["web", "terminal"] = typer.Option("terminal")) -> types.ExitCode:
    """Start the built-in webserver which runs the security management interface."""
    ts = ctx.obj.thoughtspot

    if mode == "web":
        server = Server(f"{tui.__file__} --config {ctx.obj.thoughtspot.config.name}")
        server.serve()
    else:
        ui = tui.ThoughtSpotSecurityApp(http=ts.api, ts_version=ts.session_context.thoughtspot.version)
        ui.run()

    return 0
