from __future__ import annotations

from typing import Literal

from textual_serve.server import Server
import typer

from cs_tools import errors, types
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.ux import AsyncTyper

from . import tui

app = AsyncTyper(
    help="""
    Enable querying the ThoughtSpot TQL CLI from a remote machine.

    TQL is the ThoughtSpot language for entering SQL commands. You can use TQL
    to view and modify schemas and data in tables.

    \b
    For further information on TQL, please refer to:
      https://docs.thoughtspot.com/latest/reference/sql-cli-commands.html
      https://docs.thoughtspot.com/latest/reference/tql-service-api-ref.html
    """,
)


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def interactive(
    ctx: typer.Context,
    mode: Literal["web", "terminal"] = typer.Option("terminal", help="Where to run the Remote TQL UI."),
    admin_mode: bool = typer.Option(False, "--admin", help="Enable --allow-unsafe in Remote TQL.", hidden=True),
) -> types.ExitCode:
    """
    Run an interactive TQL session as if you were on the cluster.

    TQL is a command line interface for creating schemas and performing basic
    database administration.
    """
    ts = ctx.obj.thoughtspot

    if not ts.session_context.user.is_data_manager:
        raise errors.InsufficientPrivileges(
            user=ts.session_context.user,
            service="Remote TQL",
            required_privileges=[types.GroupPrivilege.can_manage_data],
        )

    if mode == "web":
        server = Server(f"{tui.__file__} --config {ctx.obj.thoughtspot.config.name}")
        server.serve()
    else:
        ui = tui.RemoteTQLApp(sess_ctx=ts.session_context, admin_mode=admin_mode, http=ts.api)
        ui.run()

    return 0
