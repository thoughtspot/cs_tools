import pathlib

from typer import Argument as A_, Option as O_
import pydantic
import typer
import toml

from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand
from cs_tools.util import deep_update
from cs_tools.settings import TSConfig
from cs_tools.const import APP_DIR


app = typer.Typer(
    cls=CSToolsGroup,
    name='config',
    help="""
    Work with dedicated config files.

    Configuration files can be set and saved on a machine in order to eliminate
    passing cluster details and credentials to every tool.
    """
)


@app.command(cls=CSToolsCommand)
def show():
    """
    Show the location of the currently saved config files.
    """
    if not APP_DIR.exists():
        console.print('[yellow]no config files found just yet![/]')
        raise typer.Exit()

    configs = [f for f in APP_DIR.iterdir() if f.name.startswith('cluster-cfg_')]
    s = 's' if (len(configs) > 1 or len(configs) == 0) else ''

    console.print(f'Cluster configs located at: {APP_DIR}')
    console.print(f'\nFound {len(configs)} config{s}')

    for file in configs:
        console.print(f"  - {file.stem[len('cluster-cfg_'):]}")


@app.command(cls=CSToolsCommand)
def create(
    name: str=O_(..., help='config file identifier', prompt=True),
    host: str=O_(..., help='thoughtspot server', prompt=True),
    port: int=O_(None, help='optional, port of the thoughtspot server'),
    username: str=O_(..., help='username when logging into ThoughtSpot', prompt=True),
    password: str=O_(..., help='password when logging into ThoughtSpot', hide_input=True, prompt=True),
    temp_dir: pathlib.Path=O_(
        APP_DIR,
        '--temp_dir',
        help='location on disk to save temporary files',
        file_okay=False,
        resolve_path=True,
        show_default=False
    ),
    disable_ssl: bool=O_(False, '--disable_ssl', help='disable SSL verification', show_default=False),
    disable_sso: bool=O_(False, '--disable_sso', help='disable automatic SAML redirect', show_default=False),
    verbose: bool=O_(False, '--verbose', help='enable verbose logging by default', show_default=False)
):
    """
    Create a new config file.
    """
    config = TSConfig.from_cli_args(
                 host=host, username=username, password=password, temp_dir=temp_dir,
                 disable_ssl=disable_ssl, disable_sso=disable_sso, verbose=verbose
             )

    file = APP_DIR / f'cluster-cfg_{name}.toml'

    if file.exists():
        console.print(f'[red]cluster configuration file "{name}" already exists[/]')
        console.print(f'try using "cs_tools modify {name}" instead!')
        raise typer.Exit()

    with file.open('w') as t:
        toml.dump(config.dict(), t)

    console.print(f'saved cluster configuration file "{name}"')


@app.command(cls=CSToolsCommand)
def modify(
    name: str=O_(..., help='config file identifier', prompt=True),
    host: str=O_(None, help='thoughtspot server'),
    port: int=O_(None, help='optional, port of the thoughtspot server'),
    username: str=O_(None, help='username when logging into ThoughtSpot'),
    password: str=O_(None, help='password when logging into ThoughtSpot'),
    temp_dir: pathlib.Path=O_(
        None,
        '--temp_dir',
        help='location on disk to save temporary files',
        file_okay=False,
        resolve_path=True,
        show_default=False
    ),
    disable_ssl: bool=O_(None, '--disable_ssl/--no-disable_ssl', help='disable SSL verification', show_default=False),
    disable_sso: bool=O_(None, '--disable_sso/--no-disable_sso', help='disable automatic SAML redirect', show_default=False),
    verbose: bool=O_(None, '--verbose/--normal', help='enable verbose logging by default', show_default=False)
):
    """
    Modify an existing config file.
    """
    file = APP_DIR / f'cluster-cfg_{name}.toml'
    old  = TSConfig.from_toml(file).dict()

    data = TSConfig.from_cli_args(
                host=host, port=port, username=username, password=password,
                temp_dir=temp_dir, disable_ssl=disable_ssl, disable_sso=disable_sso,
                verbose=verbose, validate=False, default=False
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


@app.command(cls=CSToolsCommand)
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
