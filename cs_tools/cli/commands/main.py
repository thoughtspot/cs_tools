from __future__ import annotations

from traceback import format_exception
import contextlib
import datetime as dt
import logging
import random
import sys

from cs_tools import __project__, __version__, _compat, datastructures, errors, utils
from cs_tools.cli._logging import _setup_logging
from cs_tools.cli.ux import RICH_CONSOLE, CSToolsApp
from cs_tools.settings import _meta_config as meta
from cs_tools.updater import cs_tools_venv
from rich.align import Align
from rich.console import ConsoleRenderable
from rich.panel import Panel
from rich.text import Text
import click
import rich
import sqlalchemy as sa
import typer

log = logging.getLogger(__name__)
app = CSToolsApp(
    name="cs_tools",
    help=f"""
    :wave: [green]Welcome[/] to [b]CS Tools[/]!

    \b
    These are scripts and utilities used to assist in the development, implementation,
    and administration of your ThoughtSpot platform.

    Lost already? Check out our [cyan][link={__project__.__docs__}/tutorial/config/]Tutorial[/][/]!

    {meta.newer_version_string()}

    :sparkles: [yellow]All tools are provided as-is[/] :sparkles:
    :floppy_disk: [red]You should ALWAYS take a snapshot before you make any significant changes to your environment![/]
    """,
    add_completion=True,
    epilog=(
        f":bookmark: v{__version__} "
        f":scroll: [cyan][link={__project__.__docs__}]Documentation[/] "
        f":bug: [link={__project__.__bugs__}]Found a bug?[/] "
        f":megaphone: [link={__project__.__help__}]Feedback[/][/] "
        + (
            f":computer_disk: [green]{meta.default_config_name}[/] (default)"
            if meta.default_config_name is not None
            else ""
        )
    ),
)


@app.callback(invoke_without_command=True)
def main(version: bool = typer.Option(False, "--version", help="Show the version and exit.")):
    if version:
        RICH_CONSOLE.print(
            "\n", Panel.fit(Text(__version__, justify="center"), title="CS Tools", padding=(1, 0, 1, 0)), "\n"
        )
        raise typer.Exit(0)


def run() -> int:
    """
    Entrypoint into cs_tools.
    """
    from cs_tools.cli import _monkey  # noqa: F401
    from cs_tools.cli.commands import (
        config as config_app,
        log as log_app,
        self as self_app,
        tools as tools_app,
    )

    app.add_typer(tools_app.app)
    app.add_typer(config_app.app)
    app.add_typer(self_app.app)
    app.add_typer(log_app.app)

    CURRENT_RUNTIME = datastructures.ExecutionEnvironment()

    # first thing we do is request the database, this allows us to perform a migration if necessary
    cs_tools_venv.ensure_directories()

    _setup_logging()

    try:
        return_code = app(standalone_mode=False)
        return_code = 0 if return_code is None else return_code

    except (click.exceptions.Abort, click.exceptions.Exit, typer.Abort, typer.Exit) as e:
        return_code = getattr(e, "exit_code", 0)
        RICH_CONSOLE.print("[b yellow]Stopping -- cancelled by user..\n")

    except click.ClickException as e:
        return_code = 1
        log.error(e)
        log.debug("More info..", exc_info=True)

    except errors.CSToolsError as e:
        return_code = 1

        log.debug(e, exc_info=True)

        if _IS_CLI_PRINTABLE_ERROR := (hasattr(e, "__rich__") or isinstance(e, ConsoleRenderable)):
            RICH_CONSOLE.print(Align.center(e))
            log.debug(e, exc_info=True)
        else:
            log.error(e)
            log.debug("More info..", exc_info=True)

    except Exception as e:
        return_code = 1

        if isinstance(e, _compat.ExceptionGroup):
            log.error(f"Potentially many things broke. ({len(e.exceptions)} sub-exceptions)")

            for exception in e.exceptions:
                log.error("Something unexpected broke.", exc_info=exception)

        log.debug("whoopsie, something went wrong!", exc_info=True)

        rich_traceback = rich.traceback.Traceback(
            width=150,
            show_locals=True,
            suppress=[typer, click, contextlib],
            max_frames=25 if CURRENT_RUNTIME.is_ci or CURRENT_RUNTIME.is_dev else 10,
        )

        github_issue = "https://github.com/thoughtspot/cs_tools/issues/new/choose"
        suprised_emoji = random.choice(
            (
                ":cold_sweat:",
                ":astonished:",
                ":anguished:",
                ":person_shrugging:",
                ":sweat:",
                ":scream:",
                ":sweat_smile:",
                ":nerd_face:",
            ),
        )

        text = Panel(
            Text.from_markup(
                f"\nIf you encounter this message more than once, please help by letting us know!"
                f"\n"
                f"\n          GitHub: [b blue][link={github_issue}]{github_issue}[/link][/]"
                f"\n",
            ),
            border_style="yellow",
            title=f"{suprised_emoji}  This is an unhandled error!  {suprised_emoji}",
            subtitle="Run [b blue]cs_tools logs report[/] to send us your last error.",
        )

        RICH_CONSOLE.print(
            Align.center(rich_traceback),
            "\n",
            Align.center(text),
            "\n",
        )

    return return_code
