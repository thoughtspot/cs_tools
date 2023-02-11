from __future__ import annotations
from typing import Any, Dict
import logging

from rich.panel import Panel
from rich.text import Text
import typer
import rich

from cs_tools.programmatic import get_cs_tool
from cs_tools.cli._logging import _setup_logging
from cs_tools.settings import _meta_config
from cs_tools._version import __version__
from cs_tools.cli.ux import rich_console, CSToolsApp, CSToolsOption as Opt
from cs_tools.errors import CSToolsError
from cs_tools.const import DOCS_BASE_URL, GDRIVE_FORM, TOOLS_DIR, GH_ISSUES
from cs_tools.cli import _config, _tools, _self, _log
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


@app.callback(invoke_without_command=True)
def main(version: bool = Opt(False, "--version", help="Show the version and exit.")):
    if version:
        rich_console.print(
            "\n",
            Panel.fit(Text(__version__, justify="center"), title="CS Tools", padding=(1, 0, 1, 0)),
            "\n"
        )
        raise typer.Exit(0)


def _setup_tools(tools_app: typer.Typer, ctx_settings: Dict[str, Any]) -> None:
    ctx_settings["obj"].tools = {}

    for path in TOOLS_DIR.iterdir():
        if path.name == "__pycache__" or not path.is_dir():
            continue

        tool = get_cs_tool(path.name)

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


def run() -> int:
    """
    Entrypoint into cs_tools.
    """
    from cs_tools.cli import _monkey

    _setup_logging()
    _setup_tools(_tools.app, ctx_settings=app.info.context_settings)

    app.add_typer(_tools.app)
    app.add_typer(_config.app)
    app.add_typer(_self.app)
    app.add_typer(_log.app)

    try:
        app()

    except CSToolsError as e:
        log.debug(e, exc_info=True)
        rich_console.log(e)
        return 1

    except Exception:
        log.debug("whoopsie, something went wrong!", exc_info=True)

        import random
        import contextlib  # dependencies
        import typer       # main cli library
        import click       # supporting cli library

        traceback = rich.traceback.Traceback(
            width=150,
            extra_lines=3,
            word_wrap=False,
            show_locals=False,
            suppress=[typer, click, contextlib],
            max_frames=10,
        )

        google_forms = "https://forms.gle/sh6hyBSS2mnrwWCa9"
        github_issue = "https://github.com/thoughtspot/cs_tools/issues/new/choose"
        suprised_emoji = random.choice(
            (
                ":cold_sweat:", ":astonished:", ":anguished:", ":person_shrugging:", ":sweat:", ":scream:",
                ":sweat_smile:", ":nerd_face:"
            )
        )

        text = rich.panel.Panel(
            rich.text.Text.from_markup(
                f"\nIf you encounter this message more than once, please help by letting us know!"
                f"\n"
                f"\n    Google Forms: [b blue][link={google_forms}]{google_forms}[/link][/]"
                f"\n          GitHub: [b blue][link={github_issue}]{github_issue}[/link][/]"
                f"\n"
            ),
            border_style="yellow",
            title=f"{suprised_emoji}  This is an unhandled error!  {suprised_emoji}",
            subtitle="Run [b blue]cs_tools logs report[/] to send us your last error."
        )

        rich_console.print(
            rich.align.Align.center(traceback),
            "\n",
            rich.align.Align.center(text),
            "\n"
        )
        return 1

    return 0
