from typing import List
import datetime as dt
import logging

import horde
import typer

from cs_tools.cli.input import ConfirmationPrompt
from cs_tools.cli.ux import rich_console
from cs_tools.errors import ContentDoesNotExist
from cs_tools.types import GUID, RecordsFormat

from . import models
from . import zombie

log = logging.getLogger(__name__)


def eula(bypass: bool = False) -> None:
    """Issue a non-dismissable EULA."""
    if bypass:
        log.info("Concurrency simulation EULA has been [b yellow]bypassed[/].")
        return

    text = (
        "\n"
        ":zombie: [b yellow]Swarm is not magic![/] :mage:"
        "\n"
        "\nThis tool will simulate concurrency against your ThoughtSpot cluster as well as your database platform. "
        "\nWe will issue queries as if we are legitimate User activity in your platform."
        "\n"
        "\n[b yellow]This is no different from having these Users directly interact with the systems and will consume "
        "\nresources on both the ThoughtSpot and database platform sides![/]"
        "\n"
        "\n[b blue]You are responsible for using this tool wisely. Do you wish to continue?"
    )
    eula = ConfirmationPrompt(text, console=rich_console)

    accepted = eula.ask()

    if not accepted:
        log.info("Concurrency simulation EULA has been [b red]rejected[/].")
        raise typer.Exit(0)

    log.info("Concurrency simulation EULA has been [b green]accepted[/].")


def write_stats(syncer, *, strategy: str, stats: horde.Event) -> None:
    """Write ThoughtSpot performance stats to a syncer."""
    start_event = next(stat for stat in stats.memory if isinstance(stat.fired_event, horde.events.HordeInit))
    data = [
        {
            "request_start_time": r.request.headers["x-requested-at"],
            "metadata_guid": stat.fired_event.guid,
            "user_guid": stat.fired_event.user.guid,
            "performance_run_id": int(start_event.fired_event._created_at),
            "strategy": strategy,
            "metadata_type": stat.fired_event.metadata_type,
            "viz_id": viz_id if stat.fired_event.metadata_type == "PINBOARD_ANSWER_BOOK" else None,
            "is_success": stat.fired_event.is_success,
            "response_received_time": dt.datetime.fromisoformat(r.request.headers["x-requested-at"]) + r.elapsed,
            "latency": r.elapsed.total_seconds(),
        }
        for stat in stats.memory
        if isinstance(stat.fired_event, zombie.ThoughtSpotPerformanceEvent)
        for viz_id, r in stat.fired_event.responses.items()
    ]
    syncer.dump("ts_performance_event", data=[models.PerformanceEvent(**stat).dict() for stat in data])


def _find_all_users_with_access_to_worksheet(guid: GUID, thoughtspot) -> List[RecordsFormat]:
    user_guids = {}

    r = thoughtspot.api.security_metadata_permissions(metadata_type="LOGICAL_TABLE", guids=[guid])
    principals = [principal_guid for data in r.json().values() for principal_guid in data["permissions"]]

    for principal_guid in principals:
        try:
            users = thoughtspot.group.users_in(group_name=principal_guid, is_directly_assigned=False)
        except ContentDoesNotExist:
            users = [thoughtspot.api.user_read(user_guid=principal_guid).json()["header"]]

        for user in users:
            if user["id"] in user_guids:
                continue

            guid = user["id"]
            name = user["name"]
            user_guids[guid] = name

    return [{"guid": guid, "name": name} for guid, name in user_guids.items()]
