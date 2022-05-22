import functools as ft
import pathlib
import sys

from typer import Argument as A_, Option as O_
import typer
import rich

from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT
from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand
from cs_tools.cli.tools.common import setup_thoughtspot, teardown_thoughtspot, teardown_thoughtspot
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
    'thoughtspot',
    ft.partial(setup_thoughtspot, login=False),
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
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
    'thoughtspot',
    setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
)
def file(
    ctx: typer.Context,
    file: pathlib.Path=A_(
        ...,
        metavar='FILE.tql',
        help='path to file to execute, default to stdin'
    )
):
    """
    Run multiple commands within TQL on a remote server.
    \f
    DEV NOTE:

        This command is akin to using the shell command cat with TQL.

            cat create-schema.sql | tql
    """
    ts = ctx.obj.thoughtspot
    r = ts.tql.script(file)

    color_map = {
        'INFO': '[white]',
        'ERROR': '[red]'
    }

    for response in r:
        if 'messages' in response:
            for message in response['messages']:
                c = color_map.get(message['type'], '[yellow]')
                m = message['value']

                if m.strip() == 'Statement executed successfully.':
                    c = '[bold green]'
                if m.strip().endswith(';'):
                    c = '[cyan]'

                console.print(c + m, end='')

        if 'data' in response:
            t = rich.table.Table(*response['data'][0].keys(), box=rich.box.HORIZONTALS)
            [t.add_row(*_.values()) for _ in response['data']]
            console.print('\n', t)


@app.command(cls=CSToolsCommand)
@depends(
    'thoughtspot',
    setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
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
        console.print('[red]no valid input given to rtql command')
        raise typer.Exit()

    r = ts.tql.command(command, schema_=schema)

    color_map = {
        'INFO': '[white]',
        'ERROR': '[red]'
    }

    for response in r:
        if 'messages' in response:
            for message in response['messages']:
                c = color_map.get(message['type'], '[yellow]')
                m = message['value']

                if m.strip() == 'Statement executed successfully.':
                    c = '[bold green]'
                if m.strip().endswith(';'):
                    c = '[cyan]'

                console.print(c + m, end='')

        if 'data' in response:
            t = rich.table.Table(*response['data'][0].keys(), box=rich.box.HORIZONTALS)
            [t.add_row(*_.values()) for _ in response['data']]
            console.print('\n', t)
