from __future__ import annotations

import logging
import pathlib

from cs_tools import __version__, errors, utils
from cs_tools.cli import _analytics
from cs_tools.cli.types import Directory
from cs_tools.cli.ux import CSToolsApp, rich_console
from cs_tools.settings import (
    CSToolsConfig,
    _meta_config as meta,
)
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.updater import cs_tools_venv
from rich.align import Align
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
import typer

log = logging.getLogger(__name__)
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


@app.command(no_args_is_help=False)
def create(
    config: str = typer.Option(..., help="config file identifier", metavar="NAME"),
    url: str = typer.Option(..., help="your thoughtspot url or IP"),
    username: str = typer.Option(..., help="username when logging into ThoughtSpot"),
    password: str = typer.Option(
        None, help="the password you type on the ThoughtSpot login screen, use [b magenta]prompt[/] to type it hidden"
    ),
    secret: str = typer.Option(None, help="the trusted authentication secret key, found in the developer tab"),
    token: str = typer.Option(None, help="the V2 API bearer token"),
    default_org: int = typer.Option(None, help="org ID to sign into by default"),
    temp_dir: pathlib.Path = typer.Option(
        None, help="the temporary directory to use for uploading files", click_type=Directory()
    ),
    disable_ssl: bool = typer.Option(
        False, "--disable-ssl", help="whether or not to turn off checking the SSL certificate"
    ),
    default: bool = typer.Option(False, "--default", help="whether or not to make this the default configuration"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="enable verbose logging"),
):
    """
    Create a new config file.
    """

    if not any((password, secret, token)):
        log.error("You must specify at least one authentication method (--password, --secret, or --token)")
        raise typer.Exit()

    if CSToolsConfig.exists(name=config):
        log.warning(f'[b yellow]Configuration file "{config}" already exists.')

        if not Confirm.ask("\nDo you want to overwrite it?", console=rich_console):
            raise typer.Abort()

    if password == "prompt":
        password = rich_console.input("\nType your password [b yellow](your input is hidden)\n", password=True)

    data = {
        "name": config,
        "thoughtspot": {
            "url": url,
            "username": username,
            "password": password,
            "secret_key": secret,
            "bearer_token": token,
            "default_org": default_org,
            "disable_ssl": disable_ssl,
        },
        "verbose": verbose,
        "temp_dir": temp_dir or cs_tools_venv.tmp_dir,
    }

    data["created_in_cs_tools_version"] = __version__
    conf = CSToolsConfig.model_validate(data)
    ts = ThoughtSpot(conf)

    try:
        log.info("Checking supplied configuration..")
        ts.login()

    except errors.AuthenticationError as e:
        log.debug(e, exc_info=True)
        rich_console.print(Align.center(e))

    else:
        ts.logout()
        conf.save()
        log.info(f"Saving as {conf.name}!")

        if default:
            meta.default_config_name = config
            meta.save()

        _analytics.prompt_for_opt_in()


@app.command()
def modify(
    ctx: typer.Context,
    config: str = typer.Option(None, help="config file identifier", metavar="NAME"),
    url: str = typer.Option(None, help="your thoughtspot server"),
    username: str = typer.Option(None, help="username when logging into ThoughtSpot"),
    password: str = typer.Option(
        None, help="the password you type on the ThoughtSpot login screen, use [b magenta]prompt[/] to type it hidden"
    ),
    secret: str = typer.Option(None, help="the trusted authentication secret key"),
    token: str = typer.Option(None, help="the V2 API bearer token"),
    disable_ssl: bool = typer.Option(
        None, "--disable-ssl", help="whether or not to turn off checking the SSL certificate"
    ),
    default_org: int = typer.Option(None, help="org ID to sign into by default"),
    default: bool = typer.Option(
        None,
        "--default / --remove-default",
        help="whether or not to make this the default configuration",
    ),
):
    """
    Modify an existing config file.
    """
    data = CSToolsConfig.from_name(config, automigrate=True).dict()

    if url is not None:
        data["thoughtspot"]["url"] = url

    if username is not None:
        data["thoughtspot"]["username"] = username

    if default_org is not None:
        data["thoughtspot"]["default_org"] = default_org

    if password == "prompt":
        password = rich_console.input("\nType your password [b yellow](your input is hidden)\n", password=True)

    if password is not None:
        data["thoughtspot"]["password"] = password

    if secret is not None:
        data["thoughtspot"]["secret_key"] = secret

    if token is not None:
        data["thoughtspot"]["bearer_token"] = token

    if disable_ssl is not None:
        data["thoughtspot"]["disable_ssl"] = disable_ssl

    if default is not None:
        meta.default_config_name = config
        meta.save()

    conf = CSToolsConfig.model_validate(data)
    ts = ThoughtSpot(conf)

    # Set the context all the way up the stack, for proper error reporting.
    while ctx.parent:
        ctx.parent.obj.thoughtspot = ts
        ctx = ctx.parent

    try:
        log.info("Checking supplied configuration..")
        ts.login()

    except errors.AuthenticationError as e:
        log.debug(e, exc_info=True)
        rich_console.print(Align.center(e))

    else:
        ts.logout()
        conf.save()
        log.info(f"Saving as {conf.name}!")


@app.command()
def delete(config: str = typer.Option(..., help="config file identifier", show_default=False, metavar="NAME")):
    """
    Delete a config file.
    """
    if not CSToolsConfig.exists(name=config):
        rich_console.print(f'[b yellow]Configuration file "{config}" does not exist')
        return

    cs_tools_venv.app_dir.joinpath(f"cluster-cfg_{config}.toml").unlink()
    rich_console.print(f'removed cluster configuration file "{config}"')


@app.command()
def check(
    ctx: typer.Context,
    config: str = typer.Option(..., help="config file identifier", show_default=False, metavar="NAME"),
    orgs: bool = typer.Option(False, "--orgs", help="if specified, show a table of all the org IDs"),
):
    """
    Check your config file.
    """
    conf = CSToolsConfig.from_name(name=config, automigrate=True)
    ts = ThoughtSpot(conf)

    # Set the context all the way up the stack, for proper error reporting.
    while ctx.parent:
        ctx.parent.obj.thoughtspot = ts
        ctx = ctx.parent

    try:
        log.info("Checking supplied configuration..")
        ts.login()

    except errors.AuthenticationError as e:
        log.debug(e, exc_info=True)
        rich_console.print(Align.center(e))
        return

    if orgs:
        if not ts.session_context.thoughtspot.is_orgs_enabled:
            log.warning(f"--orgs specified, but orgs has not yet been enabled on {ts.session_context.thoughtspot.url}")

        else:
            r = ts.api.v1.session_orgs_read()
            d = r.json()

            table = Table(
                title=f"Orgs in [b green]{conf.thoughtspot.url}[/]",
                title_style="bold white",
                caption=f"Current org id {d['currentOrgId']}",
            )
            table.add_column("ID", justify="right")
            table.add_column("NAME")
            table.add_column("DESCRIPTION", max_width=75, no_wrap=True)

            for row in sorted(d.get("orgs", []), key=lambda r: r["orgName"]):
                table.add_row(str(row["orgId"]), row["orgName"], row["description"])

            rich_console.print("\n", Align.center(table), "\n")

    ts.logout()
    log.info("[b green]Success[/]!")


@app.command(no_args_is_help=False)
def show(
    config: str = typer.Option(None, help="display a particular config", show_default=False, metavar="NAME"),
    anonymous: bool = typer.Option(False, "--anonymous", help="remove personal references from the output"),
):
    """Display the currently saved config files."""
    if config:
        text = cs_tools_venv.app_dir.joinpath(f"cluster-cfg_{config}.toml").read_text()

        if anonymous:
            text = utils.anonymize(text)

        rich_console.print(Syntax(text, "toml", line_numbers=True))
        return 0

    # SHOW A TABLE OF ALL CONFIGURATIONS
    configs = []

    for file in cs_tools_venv.app_dir.iterdir():
        if file.name.startswith("cluster-cfg_"):
            config_name = file.stem.removeprefix("cluster-cfg_")
            is_default = meta.default_config_name == config_name

            if is_default:
                config_name += " [b green]<--- default[/]"

            text = Text.from_markup(f"- {config_name}")
            configs.append(text)

    listed = Text("\n").join(configs)

    rich_console.print(
        f"\n[b]ThoughtSpot[/] cluster configurations are located at"
        f"\n  [b blue][link={cs_tools_venv.app_dir}]{cs_tools_venv.app_dir}[/][/]"
        f"\n"
        f"\n:computer_disk: {len(configs)} cluster [yellow]--config[/]urations"
        f"\n{listed}"
    )
    return 0
