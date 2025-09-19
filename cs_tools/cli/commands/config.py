from __future__ import annotations

import json
import logging

from cs_tools import __version__, errors, utils
from cs_tools.cli import custom_types
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper
from cs_tools.settings import (
    CSToolsConfig,
    _meta_config as meta,
)
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.updater import cs_tools_venv
from rich.align import Align
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.text import Text
import rich
import typer

log = logging.getLogger(__name__)
app = AsyncTyper(
    name="config",
    help="""
    Work with dedicated config files.

    Configuration files can be set and saved on a machine in order to eliminate
    passing cluster details and credentials to every tool.
    """,
    epilog=f":computer_disk: [fg-success]{meta.default_config_name}[/] (default)"
    if meta.default_config_name is not None
    else "",
)


@app.command(no_args_is_help=False)
def create(
    ctx: typer.Context,
    config: str = typer.Option(..., help="config file identifier", metavar="NAME"),
    url: str = typer.Option(..., help="your thoughtspot url or IP"),
    username: str = typer.Option(..., help="username when logging into ThoughtSpot"),
    password: str = typer.Option(
        None, help="the password you type on the ThoughtSpot login screen, use [b magenta]prompt[/] to type it hidden"
    ),
    secret: str = typer.Option(None, help="the trusted authentication secret key, found in the developer tab"),
    concurrency: int = typer.Option(None, help="change the number call sending to TS, By default 15"),
    token: str = typer.Option(None, help="the V2 API bearer token"),
    default_org: int = typer.Option(None, help="org ID to sign into by default"),
    temp_dir: custom_types.Directory = typer.Option(None, help="the temporary directory to use for uploading files"),
    disable_ssl: bool = typer.Option(
        False, "--disable-ssl", help="whether or not to turn off checking the SSL certificate"
    ),
    proxy: str = typer.Option(None, help="proxy server to use to connect to ThoughtSpot"),
    default: bool = typer.Option(False, "--default", help="whether or not to make this the default configuration"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="enable verbose logging"),
):
    """Create a new config file."""

    if not any((password, secret, token)):
        log.error("You must specify at least one authentication method (--password, --secret, or --token)")
        raise typer.Exit()

    if CSToolsConfig.exists(name=config):
        log.warning(f'[fg-warn]Configuration file "{config}" already exists.')

        if not Confirm.ask("\nDo you want to overwrite it?", console=RICH_CONSOLE):
            raise typer.Abort()

    if password == "prompt":
        password = RICH_CONSOLE.input("\nType your password [fg-warn](your input is hidden)\n", password=True)

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
            "proxy": proxy,
            "concurrency": concurrency,
        },
        "verbose": verbose,
        "temp_dir": temp_dir or cs_tools_venv.subdir(".tmp"),
    }

    data["created_in_cs_tools_version"] = __version__
    conf = CSToolsConfig.model_validate(data)
    conf.save()

    try:
        command = typer.main.get_command(app).get_command(ctx, "check")
        ctx.invoke(command, config=conf.name)

    except errors.AuthenticationFailed as e:
        log.debug(e, exc_info=True)
        RICH_CONSOLE.print(Align.center(e))

    else:
        if default:
            meta.default_config_name = config
            meta.save()

    finally:
        log.info(f"Saving as {conf.name}!")


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
    concurrency: int = typer.Option(None, help="change the number call sending to TS, By default 15"),
    temp_dir: custom_types.Directory = typer.Option(None, help="the temporary directory to use for uploading files"),
    disable_ssl: bool = typer.Option(
        None, "--disable-ssl", help="whether or not to turn off checking the SSL certificate"
    ),
    default_org: int = typer.Option(None, help="org ID to sign into by default"),
    proxy: str = typer.Option(None, help="proxy server to use to connect to ThoughtSpot"),
    default: bool = typer.Option(
        None,
        "--default / --remove-default",
        help="whether or not to make this the default configuration",
    ),
):
    """Modify an existing config file."""
    data = CSToolsConfig.from_name(config, automigrate=True).dict()

    if url is not None:
        data["thoughtspot"]["url"] = url

    if username is not None:
        data["thoughtspot"]["username"] = username

    if default_org is not None:
        data["thoughtspot"]["default_org"] = default_org

    if password == "prompt":
        password = RICH_CONSOLE.input("\nType your password [fg-warn](your input is hidden)\n", password=True)

    if password is not None:
        data["thoughtspot"]["password"] = password

    if secret is not None:
        data["thoughtspot"]["secret_key"] = secret

    if token is not None:
        data["thoughtspot"]["bearer_token"] = token

    if temp_dir is not None:
        data["temp_dir"] = temp_dir

    if disable_ssl is not None:
        data["thoughtspot"]["disable_ssl"] = disable_ssl

    if proxy is not None:
        data["thoughtspot"]["proxy"] = proxy

    if concurrency is not None:
        data["thoughtspot"]["concurrency"] = concurrency

    conf = CSToolsConfig.model_validate(data)
    conf.save()

    try:
        command = typer.main.get_command(app).get_command(ctx, "check")
        ctx.invoke(command, config=conf.name)

    except errors.AuthenticationFailed as e:
        log.debug(e, exc_info=True)
        RICH_CONSOLE.print(Align.center(e))

    else:
        if default is not None:
            meta.default_config_name = config
            meta.save()

    finally:
        log.info(f"Saving as {conf.name}!")


@app.command()
def delete(config: str = typer.Option(..., help="config file identifier", show_default=False, metavar="NAME")):
    """Delete a config file."""
    if not CSToolsConfig.exists(name=config):
        log.error(f'[fg-warn]Configuration file "{config}" does not exist')
        return

    cs_tools_venv.base_dir.joinpath(f"cluster-cfg_{config}.toml").unlink()
    RICH_CONSOLE.print(f'removed cluster configuration file "{config}"')


@app.command()
def check(
    ctx: typer.Context,  # noqa: ARG001
    config: str = typer.Option(..., help="config file identifier", show_default=False, metavar="NAME"),
    anonymous: bool = typer.Option(
        False,
        "--anonymous",
        help="remove personal references from the output",
        hidden=True,
    ),
):
    """Check your config file."""
    conf = CSToolsConfig.from_name(name=config, automigrate=True)
    ts = ThoughtSpot(conf)

    log.info("Checking supplied configuration..")

    try:
        ts.login()

    except errors.AuthenticationFailed as e:
        RICH_CONSOLE.print(e)
        return 1

    sess_ctx = ts.session_context

    if anonymous:
        sess_ctx.thoughtspot.cluster_id = "00000000-00000000-00000000-00000000"
        sess_ctx.thoughtspot.cluster_name = "anonymous"
        sess_ctx.thoughtspot.url = "https://anonymous.thoughtspot.cloud/"
        sess_ctx.user.username = "anonymous"

    # fmt: off
    o = rich.panel.Panel(
        json.dumps(
            sess_ctx.environment.model_dump(exclude=["os_args"]) | sess_ctx.system.model_dump(exclude=["system", "ran_at"]),  # noqa: E501
            indent=2,
            default=str,
        ),
        title="[fg-success]System",
        box=rich.box.SIMPLE_HEAD,
    )
    # fmt: on

    t = rich.panel.Panel(
        json.dumps(
            sess_ctx.thoughtspot.model_dump(),
            indent=2,
            default=str,
        ),
        title="[fg-success]ThoughtSpot",
        box=rich.box.SIMPLE_HEAD,
    )

    u = rich.panel.Panel(
        sess_ctx.user.model_dump_json(exclude=["guid", "display_name", "email", "privileges"], indent=2),
        title="[fg-success]User",
        box=rich.box.SIMPLE_HEAD,
    )

    r = rich.panel.Panel(
        rich.columns.Columns([o, t, u], align="center"),
        title="Session Context",
        subtitle=f"cs_tools v{sess_ctx.cs_tools_version}",
        subtitle_align="right",
        border_style="fg-secondary",
    )

    RICH_CONSOLE.print(r, justify="center")

    log.info("[fg-success]Success![/]")
    return 0


@app.command(no_args_is_help=False)
def show(
    config: str = typer.Option(None, help="display a particular config", show_default=False, metavar="NAME"),
    anonymous: bool = typer.Option(False, "--anonymous", help="remove personal references from the output"),
):
    """Display the currently saved config files."""
    if config is not None and not CSToolsConfig.exists(name=config):
        log.error(f'[fg-warn]Configuration file "{config}" does not exist')
        return

    if config is not None:
        text = cs_tools_venv.base_dir.joinpath(f"cluster-cfg_{config}.toml").read_text()

        if anonymous:
            text = utils.anonymize(text)

        RICH_CONSOLE.print(Syntax(text, "toml", line_numbers=True))
        return 0

    # SHOW A TABLE OF ALL CONFIGURATIONS
    configs = []

    for file in cs_tools_venv.base_dir.iterdir():
        if file.name.startswith("cluster-cfg_"):
            config_name = file.stem.removeprefix("cluster-cfg_")
            is_default = meta.default_config_name == config_name

            if is_default:
                config_name += " [fg-success]<--- default[/]"

            text = Text.from_markup(f"- {config_name}")
            configs.append(text)

    listed = Text("\n").join(configs)

    RICH_CONSOLE.print(
        f"\n[b]ThoughtSpot[/] cluster configurations are located at"
        f"\n  [fg-secondary][link={cs_tools_venv.base_dir}]{cs_tools_venv.base_dir}[/][/]"
        f"\n"
        f"\n:computer_disk: {len(configs)} cluster [fg-warn]--config[/]urations"
        f"\n{listed}"
    )
    return 0
