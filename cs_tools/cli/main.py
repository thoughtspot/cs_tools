from typing import Dict, Any
import logging.config
import platform
import datetime as dt
import logging

import pendulum
import typer

from cs_tools.cli.dependencies.thoughtspot import thoughtspot_nologin
from cs_tools.cli.loader import CSTool
from cs_tools.settings import _meta_config
from cs_tools._version import __version__
from cs_tools._logging import _setup_logging
from cs_tools.cli.ux import rich_console, CSToolsApp
from cs_tools.const import DOCS_BASE_URL, GDRIVE_FORM, TOOLS_DIR, GH_ISSUES
from cs_tools.cli import _config, _tools, _log
from cs_tools import utils

log = logging.getLogger(__name__)
meta = _meta_config.load()
app = CSToolsApp(
    name="cs_tools",
    help=f"""
    :wave: [green]Welcome[/] to [b]CS Tools[/]!

    \b
    These are scripts and utilities used to assist in the development, implementation,
    and administration of your ThoughtSpot platform.

    Lost already? Check out our [cyan][link={DOCS_BASE_URL}/tutorial/config/]Tutorial[/][/]!

    {meta.newer_version_string()}

    :sparkles: [yellow]All tools are provided as-is[/] :sparkles:
    :floppy_disk: [red]You should ALWAYS take a snapshot before you make any significant changes to your environment![/]
    """,
    add_completion=False,
    no_args_is_help=True,
    context_settings={
        # global settings
        "help_option_names": ["--help", "-h"],
        "obj": utils.State(),
        # allow responsive console design
        "max_content_width": rich_console.width,
        # allow case-insensitive commands
        "token_normalize_func": lambda x: x.lower(),
    },
    epilog=(
        f":bookmark: v{__version__} "
        f":books: [cyan][link={DOCS_BASE_URL}]Documentation[/] "
        f"🛟 [link={GH_ISSUES}]Get Help[/] "
        f":memo: [link={GDRIVE_FORM}]Feedback[/][/] "
        + (
            f":computer_disk: [green]{meta.default_config_name}[/] (default)"
            if meta.default_config_name is not None
            else ""
        )
    ),
)


@app.command("platform", hidden=True, dependencies=[thoughtspot_nologin])
def _platform(ctx: typer.Context):
    """
    Return details about this machine for debugging purposes.
    """
    ts = ctx.obj.thoughtspot

    m = f"""[b yellow]
        [PLATFORM DETAILS]
        system: {platform.system()} (detail: {platform.platform()})
        python: {platform.python_version()}
        ran at: {pendulum.now().format('dddd, MMMM Do YYYY @ HH:mm:ss A (zz)')}
        cs_tools: v{__version__}
    """

    try:
        ts.login()
    except Exception as e:
        exc = type(e).__name__
        msg = str(e).replace("\n", "\n      ")
        m += f"""
        [LOGIN ERROR]
        {exc}: {msg}
        """
    else:
        m += f"""
        [THOUGHTSPOT]
        cluster id: {ts.platform.cluster_id}
        cluster: {ts.platform.cluster_name}
        url: {ts.platform.url}
        timezone: {ts.platform.timezone}
        branch: {ts.platform.deployment}
        version: {ts.platform.version}

        [LOGGED IN USER]
        user_id: {ts.me.guid}
        username: {ts.me.username}
        display_name: {ts.me.display_name}
        privileges: {list(map(lambda e: e.name, ts.me.privileges))}
        """
        ts.logout()

    rich_console.print(m)


# def _setup_logging() -> None:
#     now = dt.datetime.now().strftime("%Y-%m-%dT%H_%M_%S")

#     logging.config.dictConfig(
#         {
#             "version": 1,
#             "disable_existing_loggers": False,
#             "formatters": {
#                 "verbose": {
#                     "format": "[%(levelname)s - %(asctime)s] [%(name)s - %(module)s.%(funcName)s %(lineno)d] %(message)s"
#                 }
#             },
#             "handlers": {
#                 "to_file": {
#                     "formatter": "verbose",
#                     "level": "DEBUG",  # user can override in their config file
#                     "class": "logging.FileHandler",
#                     # RotatingFileHandler.__init__ params...
#                     "filename": f"{APP_DIR}/logs/{now}.log",
#                     "mode": "w",  # Create a new file for each run of cs_tools.
#                     "encoding": "utf-8",  # Handle unicode fun.
#                     "delay": True,  # Don't create a file if no logging is done.
#                 },
#                 "to_console": {
#                     "level": "INFO",
#                     "class": "rich.logging.RichHandler",
#                     # rich.__init__ params...
#                     "console": rich_console,
#                     "show_level": False,
#                     "markup": True,
#                     "log_time_format": "[%X]",
#                 },
#             },
#             "loggers": {},
#             "root": {"level": "DEBUG", "handlers": ["to_file", "to_console"]},
#         }
#     )

#     # ROTATE LOGS
#     logs_dir = APP_DIR / "logs"
#     logs_dir.mkdir(parents=True, exist_ok=True)

#     lifo = sorted(logs_dir.iterdir(), reverse=True)

#     # keep only the last 25 logfiles
#     for idx, log in enumerate(lifo):
#         if idx > 25:
#             log.unlink()

#     # SILENCE NOISY LOGS
#     logging.getLogger("urllib3").setLevel(logging.ERROR)
#     logging.getLogger("httpx").setLevel(logging.ERROR)


def _setup_tools(tools_app: typer.Typer, ctx_settings: Dict[str, Any]) -> None:
    ctx_settings["obj"].tools = {}

    for path in TOOLS_DIR.iterdir():
        if path.name == "__pycache__" or not path.is_dir():
            continue

        tool = CSTool(path)

        if tool.privacy == "unknown":
            continue

        # add tool to the global state
        ctx_settings["obj"].tools[tool.name] = tool

        # add tool to the cli
        tools_app.add_typer(
            tool.app,
            name=tool.name,
            context_settings=ctx_settings,
            rich_help_panel=tool.app.rich_help_panel,
        )


def run():
    """
    Entrypoint into cs_tools.
    """
    _setup_logging()
    _setup_tools(_tools.app, ctx_settings=app.info.context_settings)

    app.add_typer(_tools.app)
    app.add_typer(_config.app)
    app.add_typer(_log.app)

    try:
        app()
    except Exception as e:
        log.debug("whoopsie, something went wrong!", exc_info=True)

        if hasattr(e, "cli_msg_template"):
            log.info(f"[error]{e}\n")
        else:
            GF = "https://forms.gle/sh6hyBSS2mnrwWCa9"
            GH = "https://github.com/thoughtspot/cs_tools/issues/new/choose"

            from rich.traceback import Traceback
            from rich.align import Align
            from rich.panel import Panel
            from rich.text import Text
            from rich import box
            import random
            import contextlib  # dependencies
            import typer       # main cli library
            import click       # supporting cli library

            traceback = Traceback(
                width=150,
                extra_lines=3,
                word_wrap=False,
                show_locals=False,
                suppress=[typer, click, contextlib],
                max_frames=10,
            )

            suprised_emoji = random.choice(
                (
                    ":cold_sweat:", ":astonished:", ":anguished:", ":person_shrugging:", ":sweat:", ":scream:",
                    ":sweat_smile:", ":nerd_face:"
                )
            )

            text = Panel(
                Text.from_markup(
                    f"\nIf you encounter this message more than once, please help by letting us know!"
                    f"\n"
                    f"\n    Google Forms: [blue][link={GF}]{GF}[/link][/]"
                    f"\n          GitHub: [blue][link={GH}]{GH}[/link][/]"
                    f"\n"
                ),
                box.SIMPLE_HEAD,
                border_style="yellow",
                title=f"{suprised_emoji}  This is an unhandled error!  {suprised_emoji}",
                subtitle="Run [b blue]cs_tools logs report[/] to send us your last error."
            )

            # log.exception(
            #     "[yellow]This is an unhandled error!! :cold_sweat:"
            #     "\n\nIf you encounter this message more than once, please help by "
            #     "letting us know at one of the links below:"
            #     "\n\n[/][error]",
            #     suppress=[typer]
            # )
            rich_console.print(
                Align.center(traceback),
                "\n",
                Align.center(Panel(text)),
                "\n",
            )
