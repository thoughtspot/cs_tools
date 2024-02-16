from __future__ import annotations

import logging

from rich.live import Live
import httpx
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import CSToolsApp, rich_console

from . import _extended_rest_api_v1, layout, types, work

log = logging.getLogger(__name__)


app = CSToolsApp(help="""Bulk delete metadata objects from your ThoughtSpot platform.""")


@app.command(dependencies=[thoughtspot])
def single(
    ctx: typer.Context,
    object_type: types.AcceptedObjectType = typer.Option(..., help="type of the metadata to delete"),
    object_guid: str = typer.Option(..., help="guid to delete"),
):
    """
    Removes a specific object from ThoughtSpot.
    """
    ts = ctx.obj.thoughtspot
    data = work._validate_objects_exist(ts, data=[{"object_type": object_type, "object_guid": object_guid}])

    if not data:
        log.info("[red]found no valid objects to delete")
        raise typer.Exit(1)

    with Live(layout.build_table(data), console=rich_console) as display:
        try:
            type_ = data[0].object_type
            guid = data[0].object_guid
            _extended_rest_api_v1.metadata_delete(ts.api.v1, metadata_type=type_, guids=[guid])
        except httpx.HTTPStatusError:
            log.warning(f"could not delete {data[0].object_type} ({data[0].object_guid})")
            log.debug(f"could not delete {data[0].object_type} ({data[0].object_guid})", exc_info=True)
        else:
            data[0].status = ":white_heavy_check_mark:"

        display.update(layout.build_table(data), refresh=True)


@app.command(dependencies=[thoughtspot])
def from_tabular(
    ctx: typer.Context,
    syncer: DSyncer = typer.Option(
        ...,
        click_type=SyncerProtocolType(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    deletion: str = typer.Option(..., help="directive to find content to delete", rich_help_panel="Syncer Options"),
):
    """
    Remove many objects from ThoughtSpot.

    Objects to delete are limited to answers and liveboards, but can follow
    either naming convention of the ThoughtSpot API metadta type, or the name
    found in the user interface.

    \b
        +------------------------+----------------------------------------+
        |       object_type      |              object_guid               |
        +------------------------+----------------------------------------+
        |          answer        |  01234567-FAKE-GUID-FAKE-012345678900  |
        |         pinboard       |  01234567-FAKE-GUID-FAKE-012345678900  |
        |        liveboard       |  01234567-FAKE-GUID-FAKE-012345678900  |
        |           ...          |  01234567-FAKE-GUID-FAKE-012345678900  |
        |  QUESTION_ANSWER_BOOK  |  01234567-FAKE-GUID-FAKE-012345678900  |
        |  PINBOARD_ANSWER_BOOK  |  01234567-FAKE-GUID-FAKE-012345678900  |
        |           ...          |  01234567-FAKE-GUID-FAKE-012345678900  |
        +------------------------+----------------------------------------+
    """
    if syncer is not None and deletion is None:
        rich_console.print("[red]you must provide a syncer directive to --deletion")
        raise typer.Exit(-1)

    ts = ctx.obj.thoughtspot
    data = work._validate_objects_exist(ts, data=syncer.load(deletion))

    if not data:
        log.info("[red]found no valid objects to delete")
        raise typer.Exit(1)

    with Live(layout.build_table(data), console=rich_console) as display:
        for row in data:
            try:
                _extended_rest_api_v1.metadata_delete(ts.api.v1, metadata_type=row.object_type, guids=[row.object_guid])
            except httpx.HTTPStatusError:
                log.debug(f"could not delete {row.object_type} ({row.object_guid})", exc_info=True)
                continue

            row.status = ":white_heavy_check_mark:"
            display.update(layout.build_table(data), refresh=True)
