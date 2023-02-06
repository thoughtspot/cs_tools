import statistics
import traceback
import logging

from horde.environment import Environment
import horde.events
import typer
import horde

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.input import ConfirmationPrompt
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import rich_console
from cs_tools.cli.ux import CSToolsApp
from cs_tools.cli.dependencies.syncer import DSyncer

from . import strategies
from . import _async
from . import zombie
from . import models
from . import work

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
    token: str = Opt(..., metavar="GUID", help="trusted auth token"),
    worksheet: str = Opt(..., metavar="GUID", help="dependents of this worksheet will be targeted for this test run"),
    # UI parameters
    users: int = Opt(..., help="total number of users to spawn", rich_help_panel="Spawner Options"),
    spawn_rate: int = Opt(1, help="number of users to spawn each second", rich_help_panel="Spawner Options"),
    runtime: int = Opt(
        None,
        help="execution time (in seconds) of the test, omit to run forever",
        rich_help_panel="Spawner Options"
    ),
    syncer: DSyncer = Opt(
        None,
        custom_type=SyncerProtocolType(models=[models.PerformanceEvent]),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    dismiss_eula: bool = Opt(False, "--dismiss-concurrency-warning", hidden=True)
):
    """
    Target a Worksheet for concurrency testing.

    Spawn a number of users, logging into ThoughtSpot as them and loading Answers and
    Liveboards created from the Worksheet.
    """
    ts = ctx.obj.thoughtspot

    if not dismiss_eula:
        text = (
            "\n"
            ":zombie: [b yellow]Swarm is not magic![/] :mage:"
            "\n"
            "\nThis tool will simulate concurrency against your ThoughtSpot cluster as well as your database platform. "
            "\nWe will issue queries as if we are legitimate User activity in your platform."
            "\n"
            "\n[b blue]Is this okay?"
        )
        eula = ConfirmationPrompt(text, console=rich_console)

        if not eula.ask():
            raise typer.Exit(0)
        else:
            log.info("Concurrency simulation EULA has been [b green]accepted[/].")
    else:
        log.info("Concurrency simulation EULA has been [b yellow]bypassed[/].")

    env = Environment(ts.config.thoughtspot.fullpath, zombie_classes=[strategies.ScopedRandomZombie])

    log.info("Fetching all users in your platform")
    env.shared_state.secret_key = token
    env.shared_state.all_guids = [content["id"] for content in ts.metadata.dependents(guids=[worksheet])]
    env.shared_state.all_users = work._find_all_users_with_access_to_worksheet(guid=worksheet, thoughtspot=ts)

    env.create_runner("local")
    env.create_stats_recorder()
    env.events.add_listener(horde.events.ErrorInZombieTask, listener=_handle_exception)

    env.create_ui("printer")
    runner_kw = {"number_of_zombies": users, "spawn_rate": spawn_rate, "total_execution_time": runtime}
    await env.ui.printer.start(console=rich_console, **runner_kw)

    #
    #
    #

    stats = [
        {
            "user": stat.fired_event.user.username,
            "guid": stat.fired_event.guid,
            "request_start_time": stat.fired_event.request_start_time,
            "response_received_time": stat.fired_event.response_received_time,
            "latency": stat.fired_event.latency,
            "is_error": not stat.fired_event.is_success,
        }
        for stat in env.stats.memory if isinstance(stat.fired_event, zombie.ThoughtSpotPerformanceEvent)
    ]

    if not stats:
        log.warning("No Zombies finished tasks during this run.")
        raise typer.Exit(0)

    execution_time = (stats[-1]['response_received_time'] - stats[0]['request_start_time']).total_seconds()

    log.info(
        f"=== [PERFORMANCE RUN STATISTICS] ==="
        f"\n       requests made: {len(stats): >3}"
        f"\n      execution time: {execution_time: >6.2f}s"
        f"\n     latency average: {statistics.fmean([_['latency'].total_seconds() for _ in stats]): >6.2f}s"
        f"\n          error rate: {len([_ for _ in stats if _['is_error']]) / len(stats) * 100: >6.2f}%"
        f"\n===================================="
        f"\n"
    )

    if syncer is not None:
        start_event = next(stat for stat in env.stats.memory if isinstance(stat.fired_event, horde.events.HordeInit))
        data = [
            {
                "request_start_time": stat.fired_event.request_start_time,
                "metadata_guid": stat.fired_event.guid,
                "user_guid": stat.fired_event.user.guid,
                "performance_run_id": int(start_event.fired_event._created_at),
                "metadata_type": stat.fired_event.metadata_type,
                "is_success": stat.fired_event.is_success,
                "response_received_time": stat.fired_event.response_received_time,
                "latency": stat.fired_event.latency.total_seconds(),
            }
            for stat in env.stats.memory
            if isinstance(stat.fired_event, zombie.ThoughtSpotPerformanceEvent)
        ]
        syncer.dump("ts_performance_event", data=[models.PerformanceEvent(**stat).dict() for stat in data])
