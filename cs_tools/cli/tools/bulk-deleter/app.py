from __future__ import annotations

import collections
import datetime as dt
import logging
import threading
import time

from rich import box, console
from rich.align import Align
from rich.table import Table
import typer

from cs_tools import _types, utils
from cs_tools.api import workflows
from cs_tools.cli import (
    custom_types,
    progress as px,
)
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.input import ConfirmationListener
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper
from cs_tools.sync.base import Syncer

from . import models

log = logging.getLogger(__name__)

app = AsyncTyper(help="""Bulk delete metadata objects from your ThoughtSpot platform.""")


def _tick_tock(task: px.WorkTask) -> None:
    """I'm just a clock :~)"""
    while not task.finished:
        time.sleep(1)
        task.advance(step=1)


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def downstream(
    ctx: typer.Context,
    guid: _types.GUID = typer.Option(..., help="guid of the object to delete dependents of"),
    no_prompt: bool = typer.Option(False, "--no-prompt", help="disable the confirmation prompt"),
    syncer: Syncer = typer.Option(
        None,
        click_type=custom_types.Syncer(models=[models.DeleterReport]),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    directory: custom_types.Directory = typer.Option(
        None,
        help="folder/directory to export TML objects to",
        rich_help_panel="TML Export Options",
    ),
    export_only: bool = typer.Option(
        False,
        "--export-only",
        help="export all tagged content, but don't remove it from ThoughtSpot",
        rich_help_panel="TML Export Options",
    ),
) -> _types.ExitCode:
    """
    Delete all downstream dependencies of an object.

    This will not delete the GUID of the object you target.
    """
    ts = ctx.obj.thoughtspot

    TOOL_TASKS = [
        px.WorkTask(id="GATHER_METADATA", description="Fetching objects' Dependents"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {'nowhere' if syncer is None else syncer.name}"),
        px.WorkTask(id="PREVIEW_DATA", description="Sample dependent objects"),
        px.WorkTask(id="EXPORTING", description="Exporting dependents as TML"),
        px.WorkTask(id="CONFIRM", description="Confirmation Prompt"),
        px.WorkTask(id="DELETING", description="Deleting dependent objects"),
    ]

    TODAY = dt.datetime.now(tz=dt.timezone.utc)

    with px.WorkTracker("Removing downstream dependents", tasks=TOOL_TASKS) as tracker:
        with tracker["GATHER_METADATA"]:
            c = workflows.metadata.dependents(guid=guid, http=ts.api)
            _ = utils.run_sync(c)

            if not (all_metadata := _):
                log.info(f"[fg-warn]no dependents were found for {guid}")
                return 0

        with tracker["DUMP_DATA"] as this_task:
            if syncer is None:
                this_task.skip()

            else:
                d = [
                    models.DeleterReport.validated_init(
                        type=metadata_object["type"],
                        guid=metadata_object["guid"],
                        modified=metadata_object["last_modified"],
                        reported_at=TODAY,
                        author_guid=metadata_object["author_guid"],
                        author=metadata_object["author_name"],
                        name=metadata_object["name"],
                        operation="REMOVE",
                    ).model_dump()
                    for metadata_object in all_metadata
                ]

                syncer.dump("deleter_report", data=d)

        with tracker["PREVIEW_DATA"]:
            t = Table(box=box.SIMPLE_HEAD, row_styles=("dim", ""), width=150)
            t.add_column("TYPE", justify="center", width=13)  # LOGICAL_TABLE, LIVEBOARD, ANSWER
            t.add_column("NAME", no_wrap=True)
            t.add_column("AUTHOR", no_wrap=True, width=20)
            t.add_column("MODIFIED", justify="right", no_wrap=True, width=13)  # NNNN days ago

            for idx, row in enumerate(sorted(all_metadata, key=lambda row: row["last_modified"], reverse=True)):  # type: ignore
                if idx >= 15:
                    break

                t.add_row(
                    str(row["type"]).strip(),
                    str(row["name"]).strip(),
                    str(row["author_name"]).strip(),
                    f"{(TODAY - row['last_modified'].replace(tzinfo=dt.timezone.utc)).days} days ago",  # type: ignore
                )

            RICH_CONSOLE.print(Align.center(t))

        with tracker["EXPORTING"] as this_task:
            if directory is None:
                this_task.skip()

            else:
                this_task.total = len(all_metadata)

                async def _download_and_advance(guid: _types.GUID) -> None:
                    await workflows.metadata.tml_export(guid=guid, edoc_format="YAML", directory=directory, http=ts.api)
                    this_task.advance(step=1)

                c = utils.bounded_gather(
                    *(_download_and_advance(guid=_["guid"]) for _ in all_metadata), max_concurrent=4
                )
                d = utils.run_sync(c)

        if export_only:
            return 0

        with tracker["CONFIRM"] as this_task:
            if no_prompt:
                this_task.skip()
            else:
                this_task.description = "[fg-warn]Confirmation prompt"
                this_task.total = ONE_MINUTE = 60

                tracker.extra_renderable = lambda: Align.center(
                    console.Group(
                        Align.center(f"{len(all_metadata):,} objects will be deleted"),
                        "\n[fg-warn]Press [fg-success]Y[/] to proceed, or [fg-error]n[/] to cancel.",
                    )
                )

                th = threading.Thread(target=_tick_tock, args=(this_task,))
                th.start()

                kb = ConfirmationListener(timeout=ONE_MINUTE)
                kb.run()

                assert kb.response is not None, "ConfirmationListener never got a response."

                tracker.extra_renderable = None
                this_task.final()

                if kb.response.upper() == "N":
                    this_task.description = "[fg-error]Denied[/] (no deleting done)"
                    return 0
                else:
                    this_task.description = f"[fg-success]Approved[/] (deleting {len(all_metadata):,})"

        with tracker["DELETING"] as this_task:
            this_task.total = len(all_metadata)

            guids_to_delete: set[_types.GUID] = {metadata_object["guid"] for metadata_object in all_metadata}
            delete_attempts = collections.defaultdict(int)

            async def _delete_and_advance(guid: _types.GUID) -> None:
                delete_attempts[guid] += 1
                r = await ts.api.metadata_delete(guid=guid)

                if r.is_success or delete_attempts[guid] > 10:
                    guids_to_delete.discard(guid)
                    this_task.advance(step=1)

            while guids_to_delete:
                c = utils.bounded_gather(*(_delete_and_advance(guid=_) for _ in guids_to_delete), max_concurrent=15)
                _ = utils.run_sync(c)

    return 0


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def from_tag(
    ctx: typer.Context,
    tag_name: str = typer.Option(..., "--tag", help="case sensitive name to tag stale objects with"),
    tag_only: bool = typer.Option(False, "--tag-only", help="delete only the tag itself, not the objects"),
    no_prompt: bool = typer.Option(False, "--no-prompt", help="disable the confirmation prompt"),
    directory: custom_types.Directory = typer.Option(
        None,
        help="folder/directory to export TML objects to",
        rich_help_panel="TML Export Options",
    ),
    export_only: bool = typer.Option(
        False,
        "--export-only",
        help="export all tagged content, but don't remove it from ThoughtSpot",
        rich_help_panel="TML Export Options",
    ),
) -> _types.ExitCode:
    """Delete content with the identified --tag."""
    if export_only and directory is None:
        raise typer.BadParameter("You must provide a directory to export to when using --export-only.")

    ts = ctx.obj.thoughtspot

    try:
        c = workflows.metadata.fetch_one(tag_name, "TAG", http=ts.api)
        _ = utils.run_sync(c)
    except ValueError:
        raise typer.BadParameter(f"No tag found with the name '{tag_name}'") from None
    else:
        tag = _

    TOOL_TASKS = [
        px.WorkTask(id="PREPARE", description=f"Fetching objects with '{tag_name}' tag"),
        px.WorkTask(id="EXPORTING", description="Exporting objects as TML"),
        px.WorkTask(id="CONFIRM", description="Confirmation Prompt"),
        px.WorkTask(id="DELETING", description="Deleting objects"),
    ]

    with px.WorkTracker("Deleting objects", tasks=TOOL_TASKS) as tracker:
        guids_to_delete: set[_types.GUID] = {tag["metadata_id"]}

        with tracker["PREPARE"] as this_task:
            if not tag_only:
                t = ["CONNECTION", "LOGICAL_TABLE", "LIVEBOARD", "ANSWER"]
                c = workflows.metadata.fetch_all(metadata_types=t, tag_identifiers=[tag["metadata_id"]], http=ts.api)
                d = utils.run_sync(c)

                guids_to_delete.update(_["metadata_id"] for _ in d)

        with tracker["EXPORTING"] as this_task:
            if directory is None:
                this_task.skip()

            else:
                this_task.total = len(guids_to_delete)

                async def _download_and_advance(guid: _types.GUID) -> None:
                    await workflows.metadata.tml_export(guid=guid, edoc_format="YAML", directory=directory, http=ts.api)
                    this_task.advance(step=1)

                c = utils.bounded_gather(*(_download_and_advance(guid=_) for _ in guids_to_delete), max_concurrent=4)
                _ = utils.run_sync(c)

        if export_only:
            return 0

        with tracker["CONFIRM"] as this_task:
            if no_prompt:
                this_task.skip()
            else:
                this_task.description = "[fg-warn]Confirmation prompt"
                this_task.total = ONE_MINUTE = 60

                tracker.extra_renderable = lambda: Align.center(
                    console.Group(
                        Align.center(f"{len(guids_to_delete):,} objects will be deleted"),
                        "\n[fg-warn]Press [fg-success]Y[/] to proceed, or [fg-error]n[/] to cancel.",
                    )
                )

                th = threading.Thread(target=_tick_tock, args=(this_task,))
                th.start()

                kb = ConfirmationListener(timeout=ONE_MINUTE)
                kb.run()

                assert kb.response is not None, "ConfirmationListener never got a response."

                tracker.extra_renderable = None
                this_task.final()

                if kb.response.upper() == "N":
                    this_task.description = "[fg-error]Denied[/] (no deleting done)"
                    return 0
                else:
                    this_task.description = f"[fg-success]Approved[/] (deleting {len(guids_to_delete):,})"

        with tracker["DELETING"] as this_task:
            this_task.total = len(guids_to_delete)
            delete_attempts = collections.defaultdict(int)

            async def _delete_and_advance(guid: _types.GUID) -> None:
                delete_attempts[guid] += 1
                r = await ts.api.metadata_delete(guid=guid)

                if r.is_success or delete_attempts[guid] > 10:
                    guids_to_delete.discard(guid)
                    this_task.advance(step=1)

            while guids_to_delete:
                c = utils.bounded_gather(*(_delete_and_advance(guid=_) for _ in guids_to_delete), max_concurrent=15)
                _ = utils.run_sync(c)

    return 0


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def from_tabular(
    ctx: typer.Context,
    syncer: Syncer = typer.Option(
        ...,
        click_type=custom_types.Syncer(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    deletion: str = typer.Option(..., help="directive to find content to delete", rich_help_panel="Syncer Options"),
    no_prompt: bool = typer.Option(False, "--no-prompt", help="disable the confirmation prompt"),
    directory: custom_types.Directory = typer.Option(
        None,
        help="folder/directory to export TML objects to",
        rich_help_panel="TML Export Options",
    ),
    export_only: bool = typer.Option(
        False,
        "--export-only",
        help="export all tagged content, but don't remove it from ThoughtSpot",
        rich_help_panel="TML Export Options",
    ),
) -> _types.ExitCode:
    """
    Remove metadata from ThoughtSpot.

    Any valid object guid will be deleted.

    \b
        +----------------------------------------+
        |                  guid                  |
        +----------------------------------------+
        |  01234567-FAKE-GUID-FAKE-012345678900  |
        |  01234567-FAKE-GUID-FAKE-012345678900  |
        |  01234567-FAKE-GUID-FAKE-012345678900  |
        |  01234567-FAKE-GUID-FAKE-012345678900  |
        |  01234567-FAKE-GUID-FAKE-012345678900  |
        |  01234567-FAKE-GUID-FAKE-012345678900  |
        +----------------------------------------+
    """
    if syncer is not None and deletion is None:
        raise typer.BadParameter("You must provide a syncer directive to --deletion.")

    if export_only and directory is None:
        raise typer.BadParameter("You must provide a directory to export to when using --export-only.")

    ts = ctx.obj.thoughtspot

    TOOL_TASKS = [
        px.WorkTask(id="LOAD_DATA", description=f"Loading data from {syncer.name}"),
        px.WorkTask(id="EXPORTING", description="Exporting objects as TML"),
        px.WorkTask(id="CONFIRM", description="Confirmation Prompt"),
        px.WorkTask(id="DELETING", description="Deleting dependent objects"),
    ]

    with px.WorkTracker("Deleting objects", tasks=TOOL_TASKS) as tracker:
        with tracker["LOAD_DATA"]:
            all_metadata = syncer.load(deletion)

        with tracker["EXPORTING"] as this_task:
            if directory is None:
                this_task.skip()

            else:
                this_task.total = len(all_metadata)

                async def _download_and_advance(guid: _types.GUID) -> None:
                    await workflows.metadata.tml_export(guid=guid, edoc_format="YAML", directory=directory, http=ts.api)
                    this_task.advance(step=1)

                c = utils.bounded_gather(
                    *(_download_and_advance(guid=_["guid"]) for _ in all_metadata), max_concurrent=4
                )
                _ = utils.run_sync(c)

        if export_only:
            return 0

        with tracker["CONFIRM"] as this_task:
            if no_prompt:
                this_task.skip()
            else:
                this_task.description = "[fg-warn]Confirmation prompt"
                this_task.total = ONE_MINUTE = 60

                tracker.extra_renderable = lambda: Align.center(
                    console.Group(
                        Align.center(f"{len(all_metadata):,} objects will be deleted"),
                        "\n[fg-warn]Press [fg-success]Y[/] to proceed, or [fg-error]n[/] to cancel.",
                    )
                )

                th = threading.Thread(target=_tick_tock, args=(this_task,))
                th.start()

                kb = ConfirmationListener(timeout=ONE_MINUTE)
                kb.run()

                assert kb.response is not None, "ConfirmationListener never got a response."

                tracker.extra_renderable = None
                this_task.final()

                if kb.response.upper() == "N":
                    this_task.description = "[fg-error]Denied[/] (no deleting done)"
                    return 0
                else:
                    this_task.description = f"[fg-success]Approved[/] (deleting {len(all_metadata):,})"

        with tracker["DELETING"] as this_task:
            this_task.total = len(all_metadata)

            guids_to_delete: set[_types.GUID] = {metadata_object["guid"] for metadata_object in all_metadata}
            delete_attempts = collections.defaultdict(int)

            async def _delete_and_advance(guid: _types.GUID) -> None:
                delete_attempts[guid] += 1
                r = await ts.api.metadata_delete(guid=guid)

                if r.is_success or delete_attempts[guid] > 10:
                    guids_to_delete.discard(guid)
                    this_task.advance(step=1)

            while guids_to_delete:
                c = utils.bounded_gather(*(_delete_and_advance(guid=_) for _ in guids_to_delete), max_concurrent=15)
                _ = utils.run_sync(c)

    return 0
