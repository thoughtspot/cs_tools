from __future__ import annotations

import logging

from cs_tools import __version__, datastructures, errors, utils, validators
from cs_tools.cli import _analytics
from cs_tools.cli.ux import CSToolsApp, rich_console
from cs_tools.settings import (
    CSToolsConfig,
    _meta_config as meta,
)
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.updater import cs_tools_venv
from promptique.menu import Menu
from promptique.prompts import Confirm, FileInput, Select, UserInput
from promptique.prompts.select import PromptOption
from promptique.theme import PromptTheme, ThemeElement
from promptique.validation import ResponseContext, response_is
from rich.align import Align
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
import pydantic
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
    config: str = typer.Option(None, help="config file identifier", metavar="NAME"),
    url: str = typer.Option(None, help="your thoughtspot server"),
    username: str = typer.Option(None, help="username when logging into ThoughtSpot"),
    default_org: int = typer.Option(None, help="org ID to sign into by default"),
):
    """
    Create a new config file.
    """

    def buffer_is_not_empty(ctx: ResponseContext) -> bool:
        """Ensure some value is given."""
        assert len(ctx.response) != 0, "Name must be at least one character."
        return True

    def select_at_least_one(ctx: ResponseContext) -> bool:
        """Ensure some option is selected."""
        assert len(ctx.response) != 0, "You must select at least one option."
        return True

    def is_valid_url(ctx: ResponseContext) -> bool:
        """Ensure the URL given is valid."""
        try:
            validators.ensure_stringified_url_format.func(ctx.response)
        except pydantic.ValidationError:
            raise AssertionError(f"[bold green]{ctx.response or '{empty}'}[/] is not a valid URL.") from None
        return True

    prompts = (
        Select(
            id="controls",
            prompt="This menu will help you configure CS Tools.",
            detail="Use the Arrow keys to navigate, Spacebar to select, and Enter to submit, and Escape or Q to quit.",
            mode="SINGLE",
            choices=[PromptOption(text="Continue", is_selected=True)],
            transient=True,
        ),
        UserInput(
            id="config",
            prompt="Please name your configuration.",
            detail="This can be anything you want.",
            prefill=config,
            input_validator=buffer_is_not_empty,
        ),
        UserInput(
            id="url",
            prompt="What is the URL of your ThoughtSpot server?",
            detail="Make sure to include http/s.",
            prefill=url,
            input_validator=is_valid_url,
        ),
        UserInput(
            id="username",
            prompt="Who do you want to login as?",
            detail="Usernames only!",
            prefill=username,
            input_validator=buffer_is_not_empty,
        ),
        Select(
            id="auth_method",
            prompt="Which authentication method do you want to use?",
            choices=[
                PromptOption(text="Password", description="this is the password used on the ThoughtSpot login screen"),
                PromptOption(text="Trusted Authentication", description="generate a secret key from the Develop tab"),
                PromptOption(text="Bearer Token", description="generate your token from the REST API V2 playground"),
            ],
            mode="MULTI",
            selection_validator=select_at_least_one,
        ),
        Confirm(id="org_confirm", prompt="Is Orgs enabled on your cluster?", default="No"),
        Select(
            id="extras",
            prompt="Set any additional options for this configuration",
            choices=[
                PromptOption(text="Disable SSL", description="Turn off checking the SSL certificate."),
                PromptOption(text="Temporary Directory", description="Route temporary file writing to this directory."),
                PromptOption(text="Verbose Logging", description="Capture more descriptive log files."),
            ],
            mode="MULTI",
        ),
        Confirm(id="is_default", prompt="Do you want to make this the default config?", default="No"),
    )

    theme = PromptTheme()

    if "Windows" in datastructures.LocalSystemInfo().system:
        theme.active = ThemeElement(marker="◆", style=Style(color="white", bold=True))

    menu = Menu(
        *prompts,
        console=rich_console,
        intro="[white on blue]cs_tools config create",
        outro="Complete!",
        theme=theme,
    )

    #
    # Set up secondary actions
    #

    menu["config"].link(
        Confirm(
            id="config_confirm",
            prompt="A config by this name already exists, do you want to overwrite it?",
            default="No",
            choice_means_stop="No",
        ),
        validator=lambda ctx: CSToolsConfig.exists(ctx.response),
    )

    auth_info = (
        ("Password", "password", "This is the password you type when using the ThoughtSpot login screen."),
        (
            "Trusted Authentication",
            "secret key",
            "[link=https://developers.thoughtspot.com/docs/api-authv2#trusted-auth-v2]Get Secret Key[/link]",
        ),
        (
            "Bearer Token",
            "token",
            "[link=https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http/api-endpoints/authentication/get-full-access-token]Get V2 Full Access token[/link]",  # noqa: E501
        ),
    )

    for name, secret, detail in auth_info:
        menu["auth_method"].link(
            UserInput(
                id=f"auth_{secret.replace(' ', '_')}",
                prompt=f"Please enter your {secret}..",
                detail=detail,
                is_secret=secret == "password",
                input_validator=buffer_is_not_empty,
            ),
            validator=response_is(name, any_of=True),
        )

    menu["org_confirm"].link(
        UserInput(
            id="org_name",
            prompt="Type the org's id to sign in to by default..",
            prefill=default_org,
            input_validator=buffer_is_not_empty,
        ),
        validator=response_is("Yes", any_of=True),
    )

    menu["extras"].link(
        FileInput(
            id="temporary_directory",
            prompt="Where should we write temporary files to?",
            detail="This should be a permanent, valid directory.",
            path_type="DIRECTORY",
        ),
        validator=response_is("Temporary Directory", any_of=True),
    )

    menu.run()

    if menu["outro"].status == "HIDDEN":
        return

    data = {
        "name": menu["config"].buffer_as_string(),
        "thoughtspot": {
            "url": menu["url"].buffer_as_string(),
            "username": menu["username"].buffer_as_string(),
            "password": menu["auth_password"].buffer_as_string() if "auth_password" in menu else None,
            "secret_key": menu["auth_secret_key"].buffer_as_string() if "auth_secret_key" in menu else None,
            "bearer_token": menu["auth_token"].buffer_as_string() if "auth_token" in menu else None,
            "default_org": menu["org_name"].buffer_as_string() if "org_name" in menu else None,
            "disable_ssl": any(option.text == "Disable SSL" for option in menu["extras"]._response),
        },
        "verbose": any(option.text == "Verbose Logging" for option in menu["extras"]._response),
        "temp_dir": menu["temporary_directory"].buffer_as_string() if "temporary_directory" in menu else None,
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

        if menu["is_default"]._response == "Yes":
            meta.default_config_name = config
            meta.save()

        _analytics.prompt_for_opt_in()


@app.command()
def modify(
    ctx: typer.Context,
    config: str = typer.Option(None, help="config file identifier", metavar="NAME"),
    url: str = typer.Option(None, help="your thoughtspot server"),
    username: str = typer.Option(None, help="username when logging into ThoughtSpot"),
    password: str = typer.Option(None, help="the password you type when using the ThoughtSpot login screen"),
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
        password = rich_console.input("[b yellow]Type your password (your input is hidden)\n", password=True)

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
