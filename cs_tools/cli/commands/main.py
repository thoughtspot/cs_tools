from __future__ import annotations

from traceback import format_exception
import contextlib
import datetime as dt
import logging
import random
import sys

from cs_tools import __project__, __version__, datastructures, errors, utils
from cs_tools.cli import _analytics
from cs_tools.cli._logging import _setup_logging
from cs_tools.cli.ux import CSToolsApp, rich_console
from cs_tools.settings import _meta_config as meta
from cs_tools.updater import cs_tools_venv
from rich.align import Align
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
        rich_console.print(
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
    db = _analytics.get_database()

    this_run_data = {
        "envt_uuid": meta.install_uuid,
        "cs_tools_version": __version__,
        "start_dt": dt.datetime.now(tz=dt.timezone.utc),
        "os_args": " ".join(["cs_tools", *sys.argv[1:]]),
    }

    # first thing we do is request the database, this allows us to perform a migration if necessary
    cs_tools_venv.ensure_directories()

    _setup_logging()

    try:
        return_code = app(standalone_mode=False)
        return_code = 0 if return_code is None else return_code

    except (click.Abort, typer.Abort) as e:
        return_code = getattr(e, "exit_code", 0)
        rich_console.print("[b yellow]Stopping -- cancelled by user..\n")

    except click.ClickException as e:
        return_code = 1
        this_run_data["is_known_error"] = True
        this_run_data["traceback"] = utils.anonymize("\n".join(format_exception(type(e), e, e.__traceback__, limit=5)))
        log.error(e)

    except errors.CSToolsError as e:
        return_code = 1
        this_run_data["is_known_error"] = True
        this_run_data["traceback"] = utils.anonymize("\n".join(format_exception(type(e), e, e.__traceback__, limit=5)))

        log.debug(e, exc_info=True)

        if isinstance(e, errors.CSToolsCLIError):
            rich_console.print(Align.center(e))
        else:
            log.error(e)

    except Exception as e:
        return_code = 1
        this_run_data["is_known_error"] = False
        this_run_data["traceback"] = utils.anonymize("\n".join(format_exception(type(e), e, e.__traceback__, limit=5)))

        log.debug("whoopsie, something went wrong!", exc_info=True)

        rich_traceback = rich.traceback.Traceback(
            width=150,
            extra_lines=3,
            word_wrap=False,
            show_locals=False,
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

        rich_console.print(
            Align.center(rich_traceback),
            "\n",
            Align.center(text),
            "\n",
        )

    this_run_data["is_success"] = return_code in (0, None)
    this_run_data["end_dt"] = dt.datetime.now(tz=dt.timezone.utc)
    this_run = _analytics.CommandExecution.validated_init(**this_run_data, context=app.info.context_settings["obj"])

    # Add the analytics to the local database
    if not CURRENT_RUNTIME.is_dev:
        try:
            with db.begin() as transaction:
                stmt = sa.insert(_analytics.CommandExecution).values([this_run.model_dump()])
                transaction.execute(stmt)

        except sa.exc.OperationalError:
            log.debug("Error inserting data into the local analytics database", exc_info=True)

    # On CI platforms, we're running an in-process sqlite database, so we need to send at the end of every run.
    if CURRENT_RUNTIME.is_ci:
        _analytics.maybe_send_analytics_data()

    return return_code
