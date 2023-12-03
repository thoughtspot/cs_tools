from typing import List
import pathlib

from rich.prompt import Confirm, Prompt
from rich.markup import escape
import pydantic
import typer
import rich
import toml

from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.settings import _meta_config as meta, CSToolsConfig
from cs_tools.updater import cs_tools_venv
from cs_tools.errors import CSToolsError
from cs_tools.cli.ux import rich_console
from cs_tools.cli.ux import CSToolsApp
from cs_tools.cli import _analytics
from cs_tools import utils

app = CSToolsApp(
    name="config",
    help="""
    Work with dedicated config files.

    Configuration files can be set and saved on a machine in order to eliminate
    passing cluster details and credentials to every tool.
    """,
    epilog=f":computer_disk: [green]{meta.default_config_name}[/] (default)"
    if meta.default_config_name is not None
    else "",
)


@app.command()
def create(
    config: str = typer.Option(..., help="config file identifier", prompt=True, metavar="NAME"),
    host: str = typer.Option(..., help="thoughtspot server", prompt=True),
    port: int = typer.Option(None, help="optional, port of the thoughtspot server"),
    username: str = typer.Option(..., help="username when logging into ThoughtSpot", prompt=True),
    password: str = typer.Option(
        None,
        help='password when logging into ThoughtSpot, if "prompt" then hide input',
    ),
    temp_dir: pathlib.Path = typer.Option(
        cs_tools_venv.app_dir,
        "--temp_dir",
        help="location on disk to save temporary files",
        file_okay=False,
        resolve_path=True,
        show_default=False,
    ),
    disable_ssl: bool = typer.Option(False, "--disable_ssl", help="disable SSL verification", show_default=False),
    disable_sso: bool = typer.Option(False, "--disable_sso", help="disable automatic SAML redirect", show_default=False),
    syncers: List[str] = typer.Option(
        None,
        "--syncer",
        metavar="protocol://DEFINITION.toml",
        help="default definition for the syncer protocol, may be provided multiple times",
        callback=lambda ctx, to: [SyncerProtocolType().convert(_, ctx=ctx) for _ in to],
    ),
    verbose: bool = typer.Option(False, "--verbose", help="enable verbose logging by default", show_default=False),
    is_default: bool = typer.Option(False, "--default", help="set as the default configuration", show_default=False),
    overwrite: bool = typer.Option(False, "--overwrite", hidden=True),
):
    """
    Create a new config file.
    """
    if password is None or password == "prompt":
        password = Prompt.ask("[yellow](your input is hidden)[/]\nPassword", console=rich_console, password=True)

    args = {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "temp_dir": temp_dir,
        "disable_ssl": disable_ssl,
        "disable_sso": disable_sso,
        "verbose": verbose,
        "syncer": syncers,
    }
    cfg = CSToolsConfig.from_parse_args(config, **args)
    file = cs_tools_venv.app_dir / f"cluster-cfg_{config}.toml"

    if file.exists() and not overwrite and not Confirm.ask(
        f'\n[yellow]cluster configuration file "{config}" already exists, would ' f"you like to overwrite it?"
    ):
        raise typer.Exit()

    with file.open("w") as t:
        toml.dump(cfg.dict(), t)

    message = f'saved cluster configuration file "{config}"'

    if is_default:
        message += " as the default"
        meta.default_config_name = config
        meta.save()

    rich_console.print(message)
    _analytics.prompt_for_opt_in()


@app.command()
def modify(
    config: str = typer.Option(..., help="config file identifier", prompt=True, metavar="NAME"),
    host: str = typer.Option(None, help="thoughtspot server"),
    port: int = typer.Option(None, help="optional, port of the thoughtspot server"),
    username: str = typer.Option(None, help="username when logging into ThoughtSpot"),
    password: str = typer.Option(
        None,
        help='password when logging into ThoughtSpot, if "prompt" then hide input',
    ),
    temp_dir: pathlib.Path = typer.Option(
        None,
        "--temp_dir",
        help="location on disk to save temporary files",
        file_okay=False,
        resolve_path=True,
        show_default=False,
    ),
    disable_ssl: bool = typer.Option(
        None, "--disable_ssl/--no-disable_ssl", help="disable SSL verification", show_default=False
    ),
    disable_sso: bool = typer.Option(
        None, "--disable_sso/--no-disable_sso", help="disable automatic SAML redirect", show_default=False
    ),
    syncers: List[str] = typer.Option(
        None,
        "--syncer",
        metavar="protocol://DEFINITION.toml",
        help="default definition for the syncer protocol, may be provided multiple times",
        callback=lambda ctx, to: [SyncerProtocolType().convert(_, ctx=ctx) for _ in to],
    ),
    verbose: bool = typer.Option(None, "--verbose/--normal", help="enable verbose logging by default", show_default=False),
    is_default: bool = typer.Option(False, "--default", help="set as the default configuration", show_default=False),
):
    """
    Modify an existing config file.

    \f
    To modify the default syncers configured, you must supply all target syncers at
    once. eg. if you had 3 defaults set up initially, and want to remove 1, supply the
    two which are to remain.
    """
    if password == "prompt":
        password = Prompt.ask("[yellow](your input is hidden)[/]\nPassword", console=rich_console, password=True)

    file = cs_tools_venv.app_dir / f"cluster-cfg_{config}.toml"
    old = CSToolsConfig.from_toml(file).dict()
    kw = {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "temp_dir": temp_dir,
        "disable_ssl": disable_ssl,
        "disable_sso": disable_sso,
        "verbose": verbose,
        "syncer": syncers,
    }
    data = CSToolsConfig.from_parse_args(config, **kw, validate=False).dict()
    new = utils.deep_update(old, data, ignore=None)

    try:
        cfg = CSToolsConfig(**new)
    except pydantic.ValidationError as e:
        rich_console.print(f"[error]{e}")
        raise typer.Exit(1) from None

    with file.open("w") as t:
        toml.dump(cfg.dict(), t)

    message = f'saved cluster configuration file "{config}"'

    if is_default:
        message += " as the default"
        meta.default_config_name = config
        meta.save()

    rich_console.print(message)
    _analytics.prompt_for_opt_in()


@app.command()
def delete(config: str = typer.Option(..., help="config file identifier", metavar="NAME")):
    """
    Delete a config file.
    """
    file = pathlib.Path(typer.get_app_dir("cs_tools")) / f"cluster-cfg_{config}.toml"

    try:
        file.unlink()
    except FileNotFoundError:
        rich_console.print(f'[yellow]cluster configuration file "{config}" does not exist')
        raise typer.Exit(1) from None

    rich_console.print(f'removed cluster configuration file "{config}"')


@app.command()
def check(config: str = typer.Option(..., help="config file identifier", metavar="NAME")):
    """
    Check your config file.
    """
    rich_console.log(f"Checking cluster configuration [b blue]{config}")
    cfg = CSToolsConfig.from_command(config)

    rich_console.log(f'Logging into [b]ThoughtSpot[/] as [b blue]{cfg.auth["frontend"].username}')
    ts = ThoughtSpot(cfg)
    ts.login()
    ts.logout()

    rich_console.log("[secondary]Success[/]!")


@app.command(no_args_is_help=False)
def show(
    config: str = typer.Option(None, help="optionally, display the contents of a particular config", metavar="NAME"),
    anonymous: bool = typer.Option(False, "--anonymous", help="remove personal references from the output"),
):
    """
    Display the currently saved config files.
    """
    configs = [f for f in cs_tools_venv.app_dir.iterdir() if f.name.startswith("cluster-cfg_")]

    if not configs:
        raise CSToolsError(
            error=NotImplementedError("[yellow]no config files found just yet!"),
            mitigation="Run [blue]cs_tools config create --help[/] for more information",
        )

    if config is not None:
        fp = cs_tools_venv.app_dir / f"cluster-cfg_{config}.toml"

        try:
            contents = escape(fp.open().read())
        except FileNotFoundError:
            raise CSToolsError(
                error=f"could not find [blue]{config}",
                mitigation="Did you spell the cluster configuration name correctly?",
            ) from None

        not_ = " not" if config == meta.default_config_name else ""
        default = f"[b blue]{config}[/] is{not_} the [green]default[/] configuration"
        path = fp.parent.as_posix()

        if anonymous:
            path = utils.anonymize(path)
            new_contents = []

            for line in contents.split("\n"):
                if line.startswith("password"):
                    continue

                new_contents.append(utils.anonymize(line))

            contents = "\n".join(new_contents)

        text = (
            f"\n:file_folder: [link={fp.parent}]{path}[/]"
            f"\n:page_facing_up: {default}"
            "\n"
            f"\n[b blue]{contents}"
        )

        renderable = rich.panel.Panel.fit(text, padding=(0, 4, 0, 4))
        rich_console.print(renderable)
        raise typer.Exit()

    PREFIX = "cluster-cfg_"
    cfg_list = []

    for file in sorted(configs):
        cfg_name = file.stem[len(PREFIX) :]

        if meta.default_config_name == cfg_name:
            cfg_name += "\t[green]<-- default[/]"

        cfg_list.append(f"  - {cfg_name}")

    rich_console.print(
        f"\n[b]ThoughtSpot[/] cluster configurations are located at"
        f"\n  [b blue][link={cs_tools_venv.app_dir}]{cs_tools_venv.app_dir}[/][/]"
        f"\n"
        f"\n:computer_disk: {len(configs)} cluster [yellow]--config[/]urations"
        f"\n" + "\n".join(cfg_list) + "\n",
    )
