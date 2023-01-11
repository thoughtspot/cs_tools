from typing import List
import pathlib

from rich.markup import escape
from rich.prompt import Prompt, Confirm
from rich.rule import Rule
import pydantic
import typer
import toml

from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import console, CSToolsApp, CSToolsArgument as Arg, CSToolsOption as Opt
from cs_tools.settings import CSToolsConfig, _meta_config
from cs_tools.errors import CSToolsError
from cs_tools.util import deep_update
from cs_tools.const import APP_DIR

meta = _meta_config.load()
app = CSToolsApp(
    name='config',
    no_args_is_help=True,
    help="""
    Work with dedicated config files.

    Configuration files can be set and saved on a machine in order to eliminate
    passing cluster details and credentials to every tool.
    """,
    epilog=f":computer_disk: [green]{meta.default_config_name}[/] (default)" if meta.default_config_name is not None else "",
)


@app.command()
def create(
    config: str = Opt(..., help='config file identifier', prompt=True, metavar='NAME'),
    host: str = Opt(..., help='thoughtspot server', prompt=True),
    port: int = Opt(None, help='optional, port of the thoughtspot server'),
    username: str = Opt(..., help='username when logging into ThoughtSpot', prompt=True),
    password: str = Opt(
        None,
        help='password when logging into ThoughtSpot, if "prompt" then hide input',
    ),
    temp_dir: pathlib.Path = Opt(
        APP_DIR,
        '--temp_dir',
        help='location on disk to save temporary files',
        file_okay=False,
        resolve_path=True,
        show_default=False
    ),
    disable_ssl: bool = Opt(False, '--disable_ssl', help='disable SSL verification', show_default=False),
    disable_sso: bool = Opt(False, '--disable_sso', help='disable automatic SAML redirect', show_default=False),
    syncers: List[str] = Opt(
        None,
        '--syncer',
        metavar='protocol://DEFINITION.toml',
        help='default definition for the syncer protocol, may be provided multiple times',
        callback=lambda ctx, to: [SyncerProtocolType().convert(_, ctx=ctx) for _ in to]
    ),
    verbose: bool = Opt(False, '--verbose', help='enable verbose logging by default', show_default=False),
    is_default: bool = Opt(False, '--default', help='set as the default configuration', show_default=False)
):
    """
    Create a new config file.
    """
    if password is None or password == 'prompt':
        password = Prompt.ask('[yellow](your input is hidden)[/]\nPassword', console=console, password=True)

    args = {
        'host': host, 'port': port, 'username': username, 'password': password,
        'temp_dir': temp_dir, 'disable_ssl': disable_ssl, 'disable_sso': disable_sso,
        'verbose': verbose, 'syncer': syncers
    }
    cfg  = CSToolsConfig.from_parse_args(config, **args)
    file = APP_DIR / f'cluster-cfg_{config}.toml'

    if file.exists() and not Confirm.ask(
        f'\n[yellow]cluster configuration file "{config}" already exists, would '
        f'you like to overwrite it?'
    ):
        raise typer.Exit()

    with file.open('w') as t:
        toml.dump(cfg.dict(), t)

    message = f'saved cluster configuration file "{config}"'

    if is_default:
        _meta_config(config)
        message += 'as the default'

    console.print(message)


@app.command()
def modify(
    config: str = Opt(..., help='config file identifier', prompt=True, metavar='NAME'),
    host: str = Opt(None, help='thoughtspot server'),
    port: int = Opt(None, help='optional, port of the thoughtspot server'),
    username: str = Opt(None, help='username when logging into ThoughtSpot'),
    password: str = Opt(
        None,
        help='password when logging into ThoughtSpot, if "prompt" then hide input',
    ),
    temp_dir: pathlib.Path = Opt(
        None,
        '--temp_dir',
        help='location on disk to save temporary files',
        file_okay=False,
        resolve_path=True,
        show_default=False
    ),
    disable_ssl: bool = Opt(None, '--disable_ssl/--no-disable_ssl', help='disable SSL verification', show_default=False),
    disable_sso: bool = Opt(None, '--disable_sso/--no-disable_sso', help='disable automatic SAML redirect', show_default=False),
    syncers: List[str] = Opt(
        None,
        '--syncer',
        metavar='protocol://DEFINITION.toml',
        help='default definition for the syncer protocol, may be provided multiple times',
        callback=lambda ctx, to: [SyncerProtocolType().convert(_, ctx=ctx) for _ in to]
    ),
    verbose: bool = Opt(None, '--verbose/--normal', help='enable verbose logging by default', show_default=False),
    is_default: bool = Opt(False, '--default', help='set as the default configuration', show_default=False)
):
    """
    Modify an existing config file.

    \f
    To modify the default syncers configured, you must supply all target syncers at
    once. eg. if you had 3 defaults set up initially, and want to remove 1, supply the
    two which are to remain.
    """
    if password == 'prompt':
        password = Prompt.ask('[yellow](your input is hidden)[/]\nPassword', console=console, password=True)

    file = APP_DIR / f'cluster-cfg_{config}.toml'
    old  = CSToolsConfig.from_toml(file).dict()
    kw = {
        'host': host, 'port': port, 'username': username, 'password': password,
        'temp_dir': temp_dir, 'disable_ssl': disable_ssl, 'disable_sso': disable_sso,
        'verbose': verbose, 'syncer': syncers
    }
    data = CSToolsConfig.from_parse_args(config, **kw, validate=False).dict()
    new  = deep_update(old, data, ignore=None)

    try:
        cfg = CSToolsConfig(**new)
    except pydantic.ValidationError as e:
        console.print(f'[error]{e}')
        raise typer.Exit(-1)

    with file.open('w') as t:
        toml.dump(cfg.dict(), t)

    message = f'saved cluster configuration file "{config}"'

    if is_default:
        meta = _meta_config.load()
        meta.default_config_name = config
        meta.save()
        message += ' as the default'

    console.print(message)


@app.command()
def delete(
    config: str = Opt(..., help='config file identifier', metavar='NAME')
):
    """
    Delete a config file.
    """
    file = pathlib.Path(typer.get_app_dir('cs_tools')) / f'cluster-cfg_{config}.toml'

    try:
        file.unlink()
    except FileNotFoundError:
        console.print(f'[yellow]cluster configuration file "{config}" does not exist')
        raise typer.Exit()

    console.print(f'removed cluster configuration file "{config}"')


@app.command()
def check(
    config: str = Opt(..., help='config file identifier', metavar='NAME')
):
    """
    Check your config file.
    """
    console.log(f'Checking cluster configuration [b blue]{config}')
    cfg = CSToolsConfig.from_command(config)

    console.log(f'Logging into [b]ThoughtSpot[/] as [b blue]{cfg.auth["frontend"].username}')
    ts = ThoughtSpot(cfg)
    ts.login()
    ts.logout()

    console.log('[secondary]Success[/]!')


@app.command(no_args_is_help=0)  # this is abuse, pay it no mind
def show(
    config: str = Opt(
        None,
        help='optionally, display the contents of a particular config',
        metavar='NAME'
    )
):
    """
    Display the currently saved config files.
    """
    configs = [f for f in APP_DIR.iterdir() if f.name.startswith('cluster-cfg_')]

    if not configs:
        raise CSToolsError(
            error=NotImplementedError("[yellow]no config files found just yet!"),
            mitigation="Run [blue]cs_tools config create --help[/] for more information",
        )

    meta = _meta_config.load()

    if config is not None:
        fp = APP_DIR / f'cluster-cfg_{config}.toml'

        try:
            contents = escape(fp.open().read())
        except FileNotFoundError:
            raise CSToolsError(
                error=TypeError(f"could not find [blue]{config}"),
                mitigation="Did you spell the cluster configuration name correctly?",
            )

        not_ = " not" if config == meta.default_config_name else ""
        default = f"[b blue]{config}[/] is{not_} the [green]default[/] configuration"
        link = f" :computer_disk: [white][link={fp}]{fp.name}"

        console.print(
            f"\n:file_folder: [link={fp.parent}]{fp.parent}",
            f"\n:page_facing_up: {default}",
            "\n",
            Rule(title="[green]" + "~" * 10 + link, characters="~", align="left"),
            f"\n[b blue]{contents}"
        )
        raise typer.Exit()

    PREFIX = "cluster-cfg_"
    cfg_list = []

    for file in configs:
        cfg_name = file.stem[len(PREFIX):]

        if meta.default_config_name == cfg_name:
            cfg_name += '\t[green]<-- default[/]'

        cfg_list.append(f"  - {cfg_name}")

    console.print(
        f"\n[b]ThoughtSpot[/] cluster configurations are located at"
        f"\n  [b blue][link={APP_DIR}]{APP_DIR}[/][/]"
        f"\n"
        f"\n:computer_disk: {len(configs)} cluster [yellow]--config[/]urations"
        f"\n" + "\n".join(cfg_list) + "\n"
    )
