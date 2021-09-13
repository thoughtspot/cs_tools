import pathlib
import sys

from typer import Argument as A_, Option as O_
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.tools.common import run_tql_script, run_tql_command
from cs_tools.settings import TSConfig
from cs_tools.api import ThoughtSpot
from .interactive import InteractiveTQL


app = typer.Typer(
    help="""
    Enable querying the ThoughtSpot TQL CLI from a remote machine.

    TQL is the ThoughtSpot language for entering SQL commands. You can use TQL
    to view and modify schemas and data in tables.

    \b
    For further information on TQL, please refer to:
      https://docs.thoughtspot.com/latest/reference/sql-cli-commands.html
      https://docs.thoughtspot.com/latest/reference/tql-service-api-ref.html
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def interactive(
    autocomplete: bool=O_(True, '--autocomplete', help='toggle auto complete feature'),
    schema: str=O_('falcon_default_schema', help='schema name to use'),
    debug: bool=O_(False, '--debug', help='print the entire response to console'),
    **frontend_kw
):
    """
    Run an interactive TQL session as if you were on the cluster.

    TQL is a command line interface for creating schemas and performing basic
    database administration.

    For a list of all commands, type "help" after invoking tql
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)
    api = ThoughtSpot(cfg)
    tql = InteractiveTQL(api, schema=schema, autocomplete=autocomplete, console=console)
    tql.run()


@app.command(cls=RichCommand)
@frontend
def file(
    file: pathlib.Path=A_(..., help='path to file to execute, default to stdin'),
    schema: str=O_('falcon_default_schema', help='schema name to use'),
    **frontend_kw
):
    """
    Run multiple commands within TQL on a remote server.
    \f
    DEV NOTE:

        This command is akin to using the shell command cat with TQL.

            cat create-schema.sql | tql
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as api:
        run_tql_script(api, fp=file)


@app.command(cls=RichCommand)
@frontend
def command(
    command: str=A_('-', help='TQL query to execute'),
    schema: str=O_('falcon_default_schema', help='schema name to use'),
    **frontend_kw
):
    """
    Run a single TQL command on a remote server.

    By default, this command will accept input from a pipe.
    \f
    DEV NOTE:

        This command is akin to using the shell command echo with TQL.

            echo SELECT * FROM db.schema.table | tql
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    if command == '-':
        if sys.stdin.isatty():
            command = None
        else:
            command = '\n'.join(sys.stdin.readlines())

    if not command:
        console.print('[red]no valid input given to rtql command[/]')
        return

    with ThoughtSpot(cfg) as api:
        run_tql_command(api, command=command, schema=schema)
