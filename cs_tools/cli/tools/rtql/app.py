import pathlib
import sys

from typer import Argument as A_, Option as O_
import typer

from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, PASSWORD_OPT, VERBOSE_OPT
from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand
from cs_tools.cli.tools.common import run_tql_script, run_tql_command, setup_thoughtspot
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
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=setup_thoughtspot,
    options=[CONFIG_OPT, PASSWORD_OPT, VERBOSE_OPT],
    enter_exit=True
)
def interactive(
    ctx: typer.Context,
    autocomplete: bool=O_(True, '--autocomplete', help='toggle auto complete feature'),
    schema: str=O_('falcon_default_schema', help='schema name to use'),
    debug: bool=O_(False, '--debug', help='print the entire response to console'),
    http_timeout: int=O_(5.0, '--timeout', help='network call timeout threshold')
):
    """
    Run an interactive TQL session as if you were on the cluster.

    TQL is a command line interface for creating schemas and performing basic
    database administration.

    For a list of all commands, type "help" after invoking tql
    """
    ts = ctx.obj.thoughtspot
    tql = InteractiveTQL(ts, schema=schema, autocomplete=autocomplete, console=console)
    tql.run()


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=setup_thoughtspot,
    options=[CONFIG_OPT, PASSWORD_OPT, VERBOSE_OPT],
    enter_exit=True
)
def file(
    ctx: typer.Context,
    file: pathlib.Path=A_(..., metavar='FILE.tql', help='path to file to execute, default to stdin'),
    schema: str=O_('falcon_default_schema', help='schema name to use')
):
    """
    Run multiple commands within TQL on a remote server.
    \f
    DEV NOTE:

        This command is akin to using the shell command cat with TQL.

            cat create-schema.sql | tql
    """
    ts = ctx.obj.thoughtspot
    run_tql_script(ts.api, fp=file)


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=setup_thoughtspot,
    options=[CONFIG_OPT, PASSWORD_OPT, VERBOSE_OPT],
    enter_exit=True
)
def command(
    ctx: typer.Context,
    command: str=A_('-', help='TQL query to execute'),
    schema: str=O_('falcon_default_schema', help='schema name to use')
):
    """
    Run a single TQL command on a remote server.

    By default, this command will accept input from a pipe.
    \f
    DEV NOTE:

        This command is akin to using the shell command echo with TQL.

            echo SELECT * FROM db.schema.table | tql
    """
    ts = ctx.obj.thoughtspot

    if command == '-':
        if sys.stdin.isatty():
            command = None
        else:
            command = '\n'.join(sys.stdin.readlines())

    if not command:
        console.print('[red]no valid input given to rtql command[/]')
        return

    run_tql_command(ts, command=command, schema=schema)
