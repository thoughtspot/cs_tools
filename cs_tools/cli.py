import pathlib
import logging
import shutil

from typer import Argument as A_, Option as O_
import pydantic
import click
import typer
import toml

from cs_tools.helpers.cli_ux import console, RichGroup, RichCommand
from cs_tools.helpers.loader import _gather_tools
from cs_tools.util.algo import deep_update
from cs_tools.settings import TSConfig


log = logging.getLogger(__name__)


app = typer.Typer(
    help="""
    Welcome to CS Tools!

    These are scripts and utilities used to assist in the development,
    implementation, and administration of your ThoughtSpot platform.

    All tools and this library are provided as-is. While every effort
    has been made to test and certify use of these tools in the various
    supported ThoughtSpot deployments, each environment is different.

    You should ALWAYS take a snapshot before you make any significant
    changes to your environment!

    For additional help, please reach out to the ThoughtSpot Customer
    Success team.

    email: ps-na@thoughtspot.com
    """,
    cls=RichGroup,
    add_completion=False,
    context_settings={
        'help_option_names': ['--help', '-h'],
        'max_content_width': 125,
        'token_normalize_func': lambda x: x.lower()  # allow case-insensitive commands
    }
)


def _show_hidden_tool_options(
    private: bool=O_(False, '--private', hidden=True)
):
    """
    Care for the hidden options.
    """
    ctx = click.get_current_context()

    if ctx.invoked_subcommand:
        return

    if private:
        unhidden_cmds = {}

        for name, command in ctx.command.commands.items():
            if name == '__example_app__':
                continue

            command.hidden = False
            unhidden_cmds[name] = command

        ctx.command.commands = unhidden_cmds

    console.print(ctx.get_help())
    raise typer.Exit()


tools_app = typer.Typer(
    help="""
    Run an installed tool.

    Tools are a collection of different scripts to perform different functions
    which aren't native to the ThoughtSpot or advanced functionality for
    clients who have a well-adopted platform.
    """,
    cls=RichGroup,
    options_metavar='<tool-name>',
    callback=_show_hidden_tool_options,
    invoke_without_command=True
)


log_app = typer.Typer(
    help="""
    Export and view log files.

    Something went wrong? Log files will help the ThoughtSpot team understand
    how to debug and fix it.
    """,
    cls=RichGroup
)


@log_app.command(cls=RichCommand)
def export(
    save_path: pathlib.Path=A_(..., help='directory to save logs to'),
):
    """
    Grab logs to share with ThoughtSpot.
    """
    app_dir = pathlib.Path(typer.get_app_dir('cs_tools'))
    log_dir = app_dir / 'logs'

    for log in log_dir.iterdir():
        shutil.copy(log, save_path)


cfg_app = typer.Typer(
    help="""
    Work with dedicated config files.

    Configuration files can be set and saved on a machine in order to eliminate
    passing cluster details and credentials to every tool.
    """,
    cls=RichGroup
)


@cfg_app.command(cls=RichCommand)
def show():
    """
    Show the location of the currently saved config files.
    """
    app_dir = pathlib.Path(typer.get_app_dir('cs_tools'))

    if not app_dir.exists():
        console.print('[yellow]no config files found just yet![/]')
        raise typer.Exit()

    configs = [f for f in app_dir.iterdir() if f.name.startswith('cluster-cfg_')]
    s = 's' if (len(configs) > 1 or len(configs) == 0) else ''

    console.print(f'Cluster configs located at: {app_dir}')
    console.print(f'\nFound {len(configs)} config{s}')

    for file in configs:
        console.print(f"  - {file.stem[len('cluster-cfg_'):]}")


@cfg_app.command(cls=RichCommand)
def create(
    name: str=O_(..., help='config file identifier', prompt=True),
    host: str=O_(..., help='thoughtspot server', prompt=True),
    port: int=O_(None, help='optional, port of the thoughtspot server'),
    username: str=O_(..., help='username when logging into ThoughtSpot', prompt=True),
    password: str=O_(..., help='password when logging into ThoughtSpot', hide_input=True, prompt=True),
    disable_ssl: bool=O_(False, '--disable_ssl', help='disable SSL verification'),
    disable_sso: bool=O_(False, '--disable_sso', help='disable automatic SAML redirect'),
):
    """
    Create a new config file.
    """
    config = TSConfig.from_cli_args(
                 host=host, username=username, password=password, disable_ssl=disable_ssl,
                 disable_sso=disable_sso,
             )

    app_dir = pathlib.Path(typer.get_app_dir('cs_tools'))
    app_dir.mkdir(parents=True, exist_ok=True)
    file = app_dir / f'cluster-cfg_{name}.toml'

    if file.exists():
        console.print(f'[red]cluster configuration file "{name}" already exists[/]')
        console.print(f'try using "cs_tools modify {name}" instead!')
        raise typer.Exit()

    with file.open('w') as t:
        toml.dump(config.dict(), t)

    console.print(f'saved cluster configuration file "{name}"')


@cfg_app.command(cls=RichCommand)
def modify(
    name: str=O_(..., help='config file identifier', prompt=True),
    host: str=O_(None, help='thoughtspot server'),
    port: int=O_(None, help='optional, port of the thoughtspot server'),
    username: str=O_(None, help='username when logging into ThoughtSpot'),
    password: str=O_(None, help='password when logging into ThoughtSpot'),
    disable_ssl: bool=O_(None, '--disable_ssl', help='disable SSL verification'),
    disable_sso: bool=O_(None, '--disable_sso', help='disable automatic SAML redirect')
):
    """
    Modify an existing config file.
    """
    file = pathlib.Path(typer.get_app_dir('cs_tools')) / f'cluster-cfg_{name}.toml'
    old  = TSConfig.from_toml(file).dict()

    data = TSConfig.from_cli_args(
                host=host, port=port, username=username, password=password,
                disable_ssl=disable_ssl, disable_sso=disable_sso,
                validate=False, default=False
            ).dict()

    new = deep_update(old, data, ignore=None)

    try:
        config = TSConfig(**new)
    except pydantic.ValidationError as e:
        console.print(f'[error]{e}')
        raise typer.Exit(-1)

    with file.open('w') as t:
        toml.dump(config.dict(), t)

    console.print(f'saved cluster configuration file "{name}"')


@cfg_app.command(cls=RichCommand)
def delete(
    name: str=O_(..., help='config file identifier', prompt=True)
):
    """
    Delete a config file.
    """
    file = pathlib.Path(typer.get_app_dir('cs_tools')) / f'cluster-cfg_{name}.toml'

    if not file.exists():
        console.print(f'[yellow]cluster configuration file "{name}" does not exist[/]')
        raise typer.Exit()

    file.unlink()
    console.print(f'removed cluster configuration file "{name}"')


def run():
    """
    Entrypoint into cs_tools.
    """
    _gather_tools(tools_app)
    app.add_typer(tools_app, name='tools')
    app.add_typer(cfg_app, name='config')
    app.add_typer(log_app, name='logs')

    try:
        app(prog_name='cs_tools')
    except Exception as e:
        log.debug('whoopsie, something went wrong!', exc_info=True)

        if hasattr(e, 'warning'):
            e = e.warning
        else:
            e = f'{type(e).__name__}: {e}'

        console.print(f'[error]{e}')
