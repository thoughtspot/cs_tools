from __future__ import annotations

import contextlib
import logging
import random

from cs_tools import __project__, __version__, _compat, _types, datastructures, errors
from cs_tools.cli._logging import _setup_logging
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper
from cs_tools.settings import _meta_config as meta
from rich.align import Align
from rich.console import ConsoleRenderable
from rich.panel import Panel
from rich.text import Text
import click
import rich
import typer

log = logging.getLogger(__name__)
app = AsyncTyper(
    name="cs_tools",
    help=f"""
    :wave: [fg-success]Welcome[/] to CS Tools!

    \b
    {meta.newer_version_string()}

    :mage: [fg-warn]Enjoy your superpowers, but be careful![/] :sparkles:
    
    :floppy_disk: [fg-error]You should ALWAYS take a snapshot before you make any significant changes to your environment![/]
    """,
    epilog=(
        f":bookmark: v{__version__} "
        f":scroll: [cyan][link={__project__.__docs__}]Documentation[/] "
        f":bug: [link={__project__.__bugs__}]Found a bug?[/] "
        f":megaphone: [link={__project__.__help__}]Feedback[/][/] "
        + (
            f":computer_disk: [fg-success]{meta.default_config_name}[/] (default)"
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


def run() -> _types.ExitCode:
    """Entrypoint into cs_tools."""
    from cs_tools.cli import _monkey  # noqa: F401
    from cs_tools.cli.commands import (
        config as config_command,
        log as log_command,
        self as self_command,
        tools as tools_command,
    )

    tools_command._discover_tools()

    app.add_typer(tools_command.app)
    app.add_typer(config_command.app)
    app.add_typer(self_command.app)
    app.add_typer(log_command.app)

    CURRENT_RUNTIME = datastructures.ExecutionEnvironment()

    _setup_logging()

    try:
        return_code = app(standalone_mode=False)
        return_code = 0 if return_code is None else return_code

    except (click.exceptions.Abort, click.exceptions.Exit, typer.Abort, typer.Exit) as e:
        return_code = getattr(e, "exit_code", 0)
        RICH_CONSOLE.print("[fg-warn]Stopping -- cancelled by user..\n")

    except click.ClickException as e:
        return_code = 1
        log.error(f"{e.format_message()}")
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
                f"\n          GitHub: [fg-secondary][link={github_issue}]{github_issue}[/link][/]"
                f"\n",
            ),
            border_style="yellow",
            title=f"{suprised_emoji}  This is an unhandled error!  {suprised_emoji}",
            subtitle="Run [fg-secondary]cs_tools logs report[/] to send us your last error.",
        )

        RICH_CONSOLE.print(
            Align.center(rich_traceback),
            "\n",
            Align.center(text),
            "\n",
        )

    return return_code
