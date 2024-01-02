from __future__ import annotations

import pydantic
import typer

from cs_tools import utils, validators
from cs_tools.cli.prompt import Confirm, PromptMenu, PromptOption, PromptStatus, Select, UserTextInput
from cs_tools.cli.ux import CSToolsApp, rich_console
from cs_tools.settings import (
    CSToolsConfig,
    _meta_config as meta,
)
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.updater import cs_tools_venv

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
    default_org: str = typer.Option(None, help="org"),
    # temp_dir: pathlib.Path = typer.Option(
    #     cs_tools_venv.app_dir,
    #     "--temp_dir",
    #     help="location on disk to save temporary files",
    #     file_okay=False,
    #     resolve_path=True,
    #     show_default=False,
    # ),
    # disable_ssl: bool = typer.Option(False, "--disable_ssl", help="disable SSL verification", show_default=False),
    # verbose: bool = typer.Option(False, "--verbose", help="enable verbose logging by default", show_default=False),
    # is_default: bool = typer.Option(False, "--default", help="set as the default configuration", show_default=False),
):
    """
    Create a new config file.
    """

    def buffer_is_not_empty(prompt: BasePrompt, buffer: str) -> bool:
        """Ensure some value is given."""
        if len(buffer) == 0:
            prompt.warning = "Name must be at least one character."
            return False
        return True

    def select_at_least_one(prompt: BasePrompt, answer: list[PromptOption]) -> bool:
        """Ensure some option is selected."""
        if len(answer) == 0:
            prompt.warning = "You must select at least one option."
            return False
        return True

    def is_valid_url(prompt: BasePrompt, potential_url: str) -> bool:
        """Ensure the URL given is valid."""
        try:
            validators.ensure_stringified_url_format.func(potential_url)
        except pydantic.ValidationError:
            prompt.warning = f"[bold green]{potential_url or '{empty}'}[/] is not a valid URL."
            return False
        return True

    CONTROLS = Select(
        prompt="This menu will help you configure CS Tools.",
        detail="Use the Arrow keys to navigate, Spacebar to select, and Enter key to submit, and Escape or Q to quit.",
        mode="SINGLE",
        choices=[PromptOption(text="Continue", is_highlighted=True, is_selected=True)],
        transient=True,
    )
    CONFIG = UserTextInput(
        prompt="Please name your configuration.",
        detail="This can be anything you want.",
        input_validator=buffer_is_not_empty,
    )
    URL = UserTextInput(
        prompt="What is the URL of your ThoughtSpot server?",
        detail="Make sure to include http/s.",
        input_validator=is_valid_url,
    )
    USERNAME = UserTextInput(
        prompt="Who do you want to login as?", detail="Usernames only!", input_validator=buffer_is_not_empty
    )
    AUTH_METHOD = Select(
        prompt="Which authentication method do you want to use?",
        choices=[
            PromptOption(text="Password", description="this is the password used on the ThoughtSpot login screen"),
            PromptOption(text="Trusted Authentication", description="generate a secret key from the Develop tab"),
            PromptOption(text="Bearer Token", description="generate your token from the REST API V2 playground"),
        ],
        mode="MULTI",
        selection_validator=select_at_least_one,
    )
    ORG_CONFIRM = Confirm(prompt="Is Orgs enabled on your cluster?", default="No")
    IS_DEFAULT = Confirm(prompt="Do you want to make this the default config?", default="No")

    nav = PromptMenu(
        CONTROLS,
        CONFIG,
        URL,
        USERNAME,
        AUTH_METHOD,
        ORG_CONFIRM,
        IS_DEFAULT,
        console=rich_console,
        intro="[white on blue]cs_tools config create",
        outro="Complete!",
    )

    if config is not None:
        CONFIG.set_buffer(config)

    if url is not None:
        URL.set_buffer(url)

    if username is not None:
        USERNAME.set_buffer(username)

    nav.start()

    for prompt in nav.prompts:
        nav.handle_prompt(prompt)

        # Add a check for overwriting the config.
        if prompt == CONFIG and CSToolsConfig.exists(prompt.buffer_as_string()):
            nav.add(
                Confirm(
                    prompt=f"Config [b green]{prompt.buffer_as_string()}[/] exists, do you want to overwrite it?",
                    default="No",
                    choice_means_stop="No",
                ),
                after=prompt,
            )

        if prompt == AUTH_METHOD:
            secret_kind = {"Password": "password", "Trusted Authentication": "secret key", "Bearer Token": "token"}

            for secret in reversed(prompt.answer):
                secret_type = secret_kind[secret.text]
                nav.add(
                    UserTextInput(
                        prompt=f"Please enter your {secret_type}..",
                        is_secret=secret.text == "Password",
                        input_validator=buffer_is_not_empty,
                    ),
                    after=prompt,
                )

        if prompt == ORG_CONFIRM and prompt.answer[0].text == "Yes":
            nav.add(
                UserTextInput(
                    prompt="Please enter the org name you to sign in to by default..",
                    input_validator=buffer_is_not_empty,
                ),
                after=prompt,
            )

        if prompt.status in (PromptStatus.cancel(), PromptStatus.error()):
            break

    nav.stop()

    # data = {
    #     "name": nav["config"].buffer_as_string(),
    #     "thoughtspot": {
    #         "url": nav["url"].buffer_as_string(),
    #         "username": nav["username"].buffer_as_string(),
    #         "password": nav["password"].buffer_as_string(),
    #         "secret_key": nav["secret_key"].buffer_as_string(),
    #         "bearer_token": nav["bearer_token"].buffer_as_string(),
    #         "default_org": nav["default_org"].buffer_as_string(),
    #         "disable_ssl": next((True for option in nav["extras"].answer if option.text == "disable ssl"), False),
    #     },
    #     "verbose": next((True for ans in nav["extras"].answer if ans.text == "verbose"), False),
    #     "temp_dir": nav["temporary_directory"].buffer_as_string(),
    # }

    # conf = CSToolsConfig.model_validate(data)
    # conf.save()

    # _analytics.prompt_for_opt_in()


# @app.command()
# def modify(
#     config: str = typer.Option(..., help="config file identifier", prompt=True, metavar="NAME"),
#     host: str = typer.Option(None, help="thoughtspot server"),
#     port: int = typer.Option(None, help="optional, port of the thoughtspot server"),
#     username: str = typer.Option(None, help="username when logging into ThoughtSpot"),
#     password: str = typer.Option(
#         None,
#         help='password when logging into ThoughtSpot, if "prompt" then hide input',
#     ),
#     temp_dir: pathlib.Path = typer.Option(
#         None,
#         "--temp_dir",
#         help="location on disk to save temporary files",
#         file_okay=False,
#         resolve_path=True,
#         show_default=False,
#     ),
#     disable_ssl: bool = typer.Option(
#         None, "--disable_ssl/--no-disable_ssl", help="disable SSL verification", show_default=False
#     ),
#     disable_sso: bool = typer.Option(
#         None, "--disable_sso/--no-disable_sso", help="disable automatic SAML redirect", show_default=False
#     ),
#     syncers: list[str] = typer.Option(
#         None,
#         "--syncer",
#         metavar="protocol://DEFINITION.toml",
#         help="default definition for the syncer protocol, may be provided multiple times",
#         callback=lambda ctx, to: [SyncerProtocolType().convert(_, ctx=ctx) for _ in to],
#     ),
#     verbose: bool = typer.Option(
#         None, "--verbose/--normal", help="enable verbose logging by default", show_default=False
#     ),
#     is_default: bool = typer.Option(False, "--default", help="set as the default configuration", show_default=False),
# ):
#     """
#     Modify an existing config file.

#     \f
#     To modify the default syncers configured, you must supply all target syncers at
#     once. eg. if you had 3 defaults set up initially, and want to remove 1, supply the
#     two which are to remain.
#     """
#     if password == "prompt":
#         password = Prompt.ask("[yellow](your input is hidden)[/]\nPassword", console=rich_console, password=True)

#     file = cs_tools_venv.app_dir / f"cluster-cfg_{config}.toml"
#     old = CSToolsConfig.from_toml(file, automigrate=True).dict()
#     kw = {
#         "host": host,
#         "port": port,
#         "username": username,
#         "password": password,
#         "temp_dir": temp_dir,
#         "disable_ssl": disable_ssl,
#         "disable_sso": disable_sso,
#         "verbose": verbose,
#         "syncer": syncers,
#     }
#     data = CSToolsConfig.from_parse_args(config, **kw, validate=False).dict()
#     new = utils.deep_update(old, data, ignore=None)

#     try:
#         cfg = CSToolsConfig(**new)
#     except pydantic.ValidationError as e:
#         rich_console.print(f"[error]{e}")
#         raise typer.Exit(1) from None

#     with file.open("w") as t:
#         toml.dump(cfg.dict(), t)

#     message = f'saved cluster configuration file "{config}"'

#     if is_default:
#         message += " as the default"
#         meta.default_config_name = config
#         meta.save()

#     rich_console.print(message)
#     _analytics.prompt_for_opt_in()


# @app.command()
# def delete(config: str = typer.Option(..., help="config file identifier", metavar="NAME")):
#     """
#     Delete a config file.
#     """
#     file = pathlib.Path(typer.get_app_dir("cs_tools")) / f"cluster-cfg_{config}.toml"

#     try:
#         file.unlink()
#     except FileNotFoundError:
#         rich_console.print(f'[yellow]cluster configuration file "{config}" does not exist')
#         raise typer.Exit(1) from None

#     rich_console.print(f'removed cluster configuration file "{config}"')


@app.command()
def check(ctx: typer.Context, config: str = typer.Option(..., help="config file identifier", metavar="NAME")):
    """
    Check your config file.
    """
    rich_console.log(f"Checking cluster configuration [b blue]{config}")

    conf = CSToolsConfig.from_name(name=config, automigrate=True)

    rich_console.log(f"Logging into [b]ThoughtSpot[/] as [b blue]{conf.thoughtspot.username}")
    ts = ThoughtSpot(conf)
    ts.login()

    while ctx.parent:
        ctx.parent.obj.thoughtspot = ts
        ctx = ctx.parent

    ts.logout()

    rich_console.log("[secondary]Success[/]!")


@app.command(no_args_is_help=False)
def show(
    config: str = typer.Option(None, help="optionally, display the contents of a particular config", metavar="NAME"),
    anonymous: bool = typer.Option(False, "--anonymous", help="remove personal references from the output"),
):
    """Display the currently saved config files."""
    from rich.text import Text

    # SHOW A TABLE OF ALL CONFIGURATIONS
    if config is None:
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

    else:
        conf = CSToolsConfig.from_name(name=config, automigrate=True)

    return

    configs = [f for f in cs_tools_venv.app_dir.iterdir() if f.name.startswith("cluster-cfg_")]

    if not configs:
        raise CSToolsError(
            title="[yellow]no config files found just yet!",
            mitigation="Run [blue]cs_tools config create --help[/] for more information",
        )

    if config is not None:
        fp = cs_tools_venv.app_dir / f"cluster-cfg_{config}.toml"

        try:
            contents = escape(fp.open().read())
        except FileNotFoundError:
            raise CSToolsError(
                title=f"could not find [blue]{config}",
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
            f"\n:file_folder: [link={fp.parent}]{path}[/]" f"\n:page_facing_up: {default}" "\n" f"\n[b blue]{contents}"
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
