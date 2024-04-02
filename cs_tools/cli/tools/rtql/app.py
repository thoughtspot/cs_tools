from __future__ import annotations

import pathlib
import sys

import rich
import typer

from cs_tools.cli.dependencies.thoughtspot import thoughtspot, thoughtspot_nologin
from cs_tools.cli.ux import CSToolsApp, rich_console

app = CSToolsApp(
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


@app.command(dependencies=[thoughtspot_nologin])
def interactive(
    ctx: typer.Context,
    autocomplete: bool = typer.Option(False, "--autocomplete", help="toggle auto complete feature", show_default=False),
    schema: str = typer.Option("falcon_default_schema", help="schema name to use"),
    http_timeout: int = typer.Option(60.0, "--timeout", help="network call timeout threshold"),
):
    """
    Run an interactive TQL session as if you were on the cluster.

    TQL is a command line interface for creating schemas and performing basic
    database administration.

    For a list of all commands, type "help" after invoking tql
    """
    from .interactive import InteractiveTQL

    ts = ctx.obj.thoughtspot
    tql = InteractiveTQL(ts, schema=schema, autocomplete=autocomplete, console=rich_console, http_timeout=http_timeout)
    tql.run()


@app.command(dependencies=[thoughtspot])
def file(
    ctx: typer.Context,
    file: pathlib.Path = typer.Argument(..., metavar="FILE.tql", help="path to file to execute, default to stdin"),
    http_timeout: int = typer.Option(60.0, "--timeout", help="network call timeout threshold"),
):
    """
    Run multiple commands within TQL on a remote server.
    """
    ts = ctx.obj.thoughtspot
    r = ts.tql.script(file, http_timeout=http_timeout)

    color_map = {"INFO": "[white]", "ERROR": "[red]"}

    for response in r:
        if "messages" in response:
            for message in response["messages"]:
                c = color_map.get(message["type"], "[yellow]")
                m = message["value"]

                if m.strip() == "Statement executed successfully.":
                    c = "[bold green]"
                if m.strip().endswith(";"):
                    c = "[cyan]"

                rich_console.print(c + m, end="")

        if "data" in response:
            t = rich.table.Table(*response["data"][0].keys(), box=rich.box.HORIZONTALS)
            [t.add_row(*_.values()) for _ in response["data"]]
            rich_console.print("\n", t)


@app.command(dependencies=[thoughtspot])
def command(
    ctx: typer.Context,
    command: str = typer.Argument("-", help="TQL query to execute", metavar='"SELECT ..."'),
    schema: str = typer.Option("falcon_default_schema", help="schema name to use"),
    http_timeout: int = typer.Option(60.0, "--timeout", help="network call timeout threshold"),
):
    """
    Run a single TQL command on a remote server.

    By default, this command will accept input from a pipe.
    """
    ts = ctx.obj.thoughtspot

    if command == "-":
        if sys.stdin.isatty():
            command = None
        else:
            command = "\n".join(sys.stdin.readlines())

    if not command:
        rich_console.print("[red]no valid input given to rtql command")
        raise typer.Exit()

    r = ts.tql.command(command, schema_=schema, http_timeout=http_timeout)

    color_map = {"INFO": "[white]", "ERROR": "[red]"}

    for response in r:
        if "messages" in response:
            for message in response["messages"]:
                c = color_map.get(message["type"], "[yellow]")
                m = message["value"]

                if m.strip() == "Statement executed successfully.":
                    c = "[bold green]"
                if m.strip().endswith(";"):
                    c = "[cyan]"

                rich_console.print(c + m, end="")

        if "data" in response:
            t = rich.table.Table(*response["data"][0].keys(), box=rich.box.HORIZONTALS)
            [t.add_row(*_.values()) for _ in response["data"]]
            rich_console.print("\n", t)
