import traceback
import logging

from horde.environment import Environment
import horde.events
import typer
import horde

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import SyncerProtocolType

from cs_tools.cli.ux import rich_console
from cs_tools.cli.ux import CSToolsApp
from cs_tools.cli.dependencies.syncer import DSyncer

from . import strategies
from . import _async
from . import models
from . import work
from . import ui

log = logging.getLogger(__name__)
app = CSToolsApp(help="Run automated tests against your ThoughtSpot cluster.")


def _handle_exception(event: horde.events.Event) -> None:
    """Print out the errors which happen in a Zombie."""
    tb_list_str = traceback.format_exception(type(event.exception), event.exception, event.exception.__traceback__)

    log.error(
        f"Unhandled error in Zombie #{event.zombie.zombie_id} -> {event.zombie_task.__name__}()"
        f"\n{''.join(tb_list_str)}"
    )


@app.command(dependencies=[thoughtspot])
@_async.coro
async def random_access(
    ctx: typer.Context,
    token: str = typer.Option(..., metavar="GUID", help="trusted auth token"),
    worksheet: str = typer.Option(..., metavar="GUID", help="dependents of this worksheet will be targeted for this test run"),
    # UI parameters
    users: int = typer.Option(..., help="total number of users to spawn", rich_help_panel="Spawner Options"),
    spawn_rate: int = typer.Option(1, help="number of users to spawn each second", rich_help_panel="Spawner Options"),
    runtime: int = typer.Option(
        None,
        help="execution time (in seconds) of the test, omit to run forever",
        rich_help_panel="Spawner Options"
    ),
    syncer: DSyncer = typer.Option(
        None,
        custom_type=SyncerProtocolType(models=[models.PerformanceEvent]),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    dismiss_eula: bool = typer.Option(False, "--dismiss-concurrency-warning", hidden=True)
):
    """
    Target a Worksheet for concurrency testing.

    Spawn a number of users, logging into ThoughtSpot as them and loading Answers and
    Liveboards created from the Worksheet.
    """
    ts = ctx.obj.thoughtspot
    work.eula(bypass=dismiss_eula)

    env = Environment(ts.config.thoughtspot.fullpath, zombie_classes=[strategies.ScopedRandomZombie])

    log.info("Fetching all users in your platform")
    env.shared_state.secret_key = token
    env.shared_state.all_guids = [content["id"] for content in ts.metadata.dependents(guids=[worksheet])]
    env.shared_state.all_users = work._find_all_users_with_access_to_worksheet(guid=worksheet, thoughtspot=ts)

    env.create_runner("local")
    env.create_stats_recorder()
    env.events.add_listener(horde.events.ErrorInZombieTask, listener=_handle_exception)

    # env.create_ui(ui.SwarmUI, ui_name="swarm")
    env.create_ui("printer")
    runner_kw = {"number_of_zombies": users, "spawn_rate": spawn_rate, "total_execution_time": runtime}
    await env.ui.printer.start(console=rich_console, **runner_kw)

    if syncer is not None:
        work.write_stats(syncer, strategy="random access", stats=env.stats)


# @app.command(dependencies=[thoughtspot])
# @_async.coro
# async def content_opens(
#     ctx: typer.Context,
#     token: str = typer.Option(..., metavar="GUID", help="trusted auth token"),
#     worksheet: str = typer.Option(..., metavar="GUID", help="dependents of this worksheet will be targeted for this test run"),
#     # Spawner Options
#     users: int = typer.Option(..., help="total number of users to spawn", rich_help_panel="Spawner Options"),
#     spawn_rate: int = typer.Option(1, help="number of users to spawn each second", rich_help_panel="Spawner Options"),
#     runtime: int = typer.Option(
#         None,
#         help="execution time (in seconds) of the test, omit to run forever",
#         rich_help_panel="Spawner Options"
#     ),
#     # Syncer Options
#     syncer: DSyncer = typer.Option(
#         None,
#         custom_type=SyncerProtocolType(models=[models.PerformanceEvent]),
#         help="protocol and path for options to pass to the syncer",
#         rich_help_panel="Syncer Options",
#     ),
#     # Hidden Options
#     dismiss_eula: bool = typer.Option(False, "--dismiss-concurrency-warning", hidden=True)
# ):
#     """
#     Target a Worksheet for concurrency testing.

#     Spawn a number of users, logging into ThoughtSpot as them and loading Answers and
#     Liveboards created from the Worksheet.
#     """
#     ts = ctx.obj.thoughtspot

#     if dismiss_eula:
#         log.info("Concurrency simulation EULA has been [b yellow]bypassed[/].")
#     else:
#         work.eula()
#         log.info("Concurrency simulation EULA has been [b green]accepted[/].")

#     env = Environment(ts.config.thoughtspot.fullpath, zombie_classes=[strategies.ScopedRandomZombie])

#     log.info("Fetching all users in your platform")
#     env.shared_state.secret_key = token
#     # env.shared_state.all_guids = [content["id"] for content in ts.metadata.dependents(guids=[worksheet])]
#     # env.shared_state.all_users = work._find_all_users_with_access_to_worksheet(guid=worksheet, thoughtspot=ts)

#     raise

#     env.create_runner("local")
#     env.create_stats_recorder()
#     env.events.add_listener(horde.events.ErrorInZombieTask, listener=_handle_exception)

#     env.create_ui("printer")
#     runner_kw = {"number_of_zombies": users, "spawn_rate": spawn_rate, "total_execution_time": runtime}
#     await env.ui.printer.start(console=rich_console, **runner_kw)

#     if syncer is not None:
#         work.write_stats(syncer, stats=env.stats)
