from __future__ import annotations

from collections.abc import Coroutine
from typing import Literal
import datetime as dt
import itertools as it
import logging
import pathlib
import threading
import time

from rich import box, console
from rich.align import Align
from rich.table import Table
import typer

from cs_tools import types, utils
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

_DEFAULT_TAG_NAME = "INACTIVE"
_ALL_BI_SERVER_HISTORY_IMPOSSIBLE_THRESHOLD_VALUE = 365 * 10


def _tick_tock(task: px.WorkTask) -> None:
    """I'm just a clock :~)"""
    while not task.finished:
        time.sleep(1)
        task.advance(step=1)


app = AsyncTyper(
    help="""
    Manage stale answers and liveboards within your platform.

    As your platform grows, user-generated content will naturally grow. Sometimes, users
    will create content for temporary exploratory purposes and then abandon it for newer
    pursuits. Archiver enables you to identify, tag, export, and remove that potentially
    abandoned content.
    """,
)


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def identify(
    ctx: typer.Context,
    tag_name: str = typer.Option(_DEFAULT_TAG_NAME, "--tag", help="case sensitive name to tag stale objects with"),
    dry_run: bool = typer.Option(False, "--dry-run", help="test your selection criteria (doesn't apply the tag)"),
    no_prompt: bool = typer.Option(False, "--no-prompt", help="disable the confirmation prompt"),
    content: Literal["ANSWER", "LIVEBOARD", "ALL"] = typer.Option(
        "ALL",
        help="type of content to mark for archival",
        rich_help_panel="Content Identification Criteria",
    ),
    recent_activity: int = typer.Option(
        _ALL_BI_SERVER_HISTORY_IMPOSSIBLE_THRESHOLD_VALUE,
        help=(
            "content without recent query activity are [fg-success]selected[/] (exceeding K days) "
            # FAKE THE DEFAULT VALUE IN THE CLI OUTPUT
            r"[dim]\[default: all TS: BI history][/]"
        ),
        show_default=False,
        rich_help_panel="Content Identification Criteria",
    ),
    recent_modified: int = typer.Option(
        100,
        help="content without recent edits will be [fg-success]selected[/] (exceeds days threshold)",
        rich_help_panel="Content Identification Criteria",
    ),
    only_groups: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="content not authored by users in these groups will be [fg-error]filtered[/], comma separated",
        show_default=False,
        rich_help_panel="Content Identification Criteria",
    ),
    ignore_groups: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="content authored by users in these groups will be [fg-error]filtered[/], comma separated",
        show_default=False,
        rich_help_panel="Content Identification Criteria",
    ),
    ignore_tags: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="content with this tag (case sensitive) will be [fg-error]filtered[/], comma separated",
        show_default=False,
        rich_help_panel="Content Identification Criteria",
    ),
    syncer: Syncer = typer.Option(
        None,
        click_type=custom_types.Syncer(models=[models.ArchiverReport]),
        help="protocol and path for options to pass to the syncer",
        show_default=False,
        rich_help_panel="Syncer Options",
    ),
) -> types.ExitCode:
    """
    Identify content which can be archived.

    \b
    :police_car_light: [fg-warn]Content owned by system level accounts ([fg-primary]tsadmin[/], [fg-primary]system[/], [fg-primary]etc[/].) will be ignored.[/] :police_car_light:
    """
    if None not in (only_groups, ignore_groups):
        RICH_CONSOLE.log("[fg-error]Select either [fg-secondary]--only-groups[/] or [fg-secondary]--include-groups[/], but not both!")
        return 1

    ts = ctx.obj.thoughtspot

    TOOL_TASKS = [
        px.WorkTask(id="GATHER_ACTIVITY", description="Fetching objects' Activity"),
        px.WorkTask(id="GATHER_METADATA", description="Fetching objects' Info"),
        px.WorkTask(id="FILTER_METADATA", description="Filtering based on your criteria"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {'nowhere' if syncer is None else syncer.name}"),
        px.WorkTask(id="PREVIEW_DATA", description=f"Sample [fg-secondary]{tag_name}[/] objects"),
        px.WorkTask(id="CONFIRM", description="Confirmation Prompt"),
        px.WorkTask(id="ARCHIVE_TAGGING", description=f"Applying [fg-secondary]{tag_name}[/] to objects"),
    ]

    TODAY = dt.datetime.now(tz=dt.timezone.utc)

    with px.WorkTracker("Identifying Stale Objects", tasks=TOOL_TASKS) as tracker:
        with tracker["GATHER_ACTIVITY"]:
            if recent_activity == _ALL_BI_SERVER_HISTORY_IMPOSSIBLE_THRESHOLD_VALUE:
                c = workflows.search(worksheet="TS: BI Server", query="min [Timestamp]", http=ts.api)
                _ = utils.run_sync(c)

                ts_bi_lifetime = TODAY - _[0]["Minimum Timestamp"].replace(tzinfo=dt.timezone.utc)
                recent_activity = ts_bi_lifetime.days + 1

            ONE_WEEK = 7

            SEARCH_TOKENS = (
                # SELECT TS: BI ACTIVITY ON ANY ACTIVITY WITH A QUERY
                "[query text] != '{null}' "
                # FILTER OUT AD-HOC SEARCH
                "[user action] != [user action].answer_unsaved "
                # FILTER OUT POTENTIAL DATA QUALITY ISSUES ? (just here for safety~)
                "[answer book guid] != '{null}' "
                # RETURN COLUMN SHOULD BE THE METADATA_GUID
                "[answer book guid]"
            )

            coros: list[Coroutine] = []

            for window_beg, window_end in it.pairwise([*range(recent_activity, -1, -ONE_WEEK), 0]):
                when = f" [timestamp] >= '{window_beg} days ago' [timestamp] < '{window_end} days ago'"
                coros.append(workflows.search(worksheet="TS: BI Server", query=SEARCH_TOKENS + when, http=ts.api))

            c = utils.bounded_gather(*coros, max_concurrent=4)  # type: ignore[assignment]
            d = utils.run_sync(c)

            active_guids = {row["Answer Book GUID"] for row in it.chain.from_iterable(d)}

        with tracker["GATHER_METADATA"]:
            if only_groups or ignore_groups:
                c = workflows.paginator(ts.api.groups_search, record_size=150_000, timeout=60 * 15)
                d = utils.run_sync(c)

                all_groups = [
                    {
                        "guid": group["id"],
                        "name": group["name"],
                        "users": group["users"],
                    }
                    for group in d
                ]

                only_groups = [group["guid"] for group in all_groups if group["name"] in (only_groups or [])]  # type: ignore[assignment]
                ignore_groups = [group["guid"] for group in all_groups if group["name"] in (ignore_groups or [])]  # type: ignore[assignment]

            if ignore_tags:
                c = workflows.metadata.fetch_all(metadata_types=["TAG"], http=ts.api)
                d = utils.run_sync(c)

                all_tags = [
                    {
                        "guid": metadata_object["metadata_id"],
                        "name": metadata_object["metadata_name"],
                    }
                    for metadata_object in d
                ]

                ignore_tags = [tag["guid"] for tag in all_tags if tag["name"] in ignore_tags]  # type: ignore[assignment]

            content = ["ANSWER", "LIVEBOARD"] if content == "ALL" else [content]  # type: ignore[assignment]
            c = workflows.metadata.fetch_all(metadata_types=content, http=ts.api)  # type: ignore[arg-type]
            d = utils.run_sync(c)

            all_metadata = [
                {
                    "guid": metadata_object["metadata_id"],
                    "name": metadata_object["metadata_name"],
                    "type": metadata_object["metadata_type"],
                    "author_guid": metadata_object["metadata_header"]["author"],
                    "author_name": metadata_object["metadata_header"]["authorName"],
                    "tags": metadata_object["metadata_header"]["tags"],
                    "last_modified": dt.datetime.fromtimestamp(
                        metadata_object["metadata_header"]["modified"] / 1000, tz=dt.timezone.utc
                    ),
                }
                for metadata_object in d
            ]

        with tracker["FILTER_METADATA"] as this_task:
            this_task.total = len(all_metadata)
            STALE_MODIFICATION_DAYS = dt.timedelta(days=recent_modified)

            filtered: types.TableRowsFormat = []

            for metadata_object in all_metadata:
                # DEV NOTE: @boonhapus, 2024/11/25
                # ALL CONDITIONS MUST PASS IN ORDER FOR AN OBJECT TO BE CONSIDERED
                # STALE. IF ANY ONE CONDITION FAILS, THE OBJECT IS SKIPPED.
                #
                checks: list[bool] = []

                # CHECK: NO TS: BI ACTIVITY WITHIN X DAYS
                checks.append(metadata_object["guid"] not in active_guids)

                # CHECK: NO MODIFICATIONS WITHIN Y DAYS
                checks.append((TODAY - metadata_object["last_modified"]) >= STALE_MODIFICATION_DAYS)

                # CHECK: THE AUTHOR IS A MEMBER OF GROUPS WHOSE CONTENT SHOULD NEEDS TO INCLUDED.
                if only_groups is not None:
                    assert isinstance(only_groups, list), "Only Groups wasn't properly transformed to an array<GUID>."
                    checks.append(metadata_object["author_guid"] in only_groups)

                # CHECK: THE AUTHOR IS NOT A MEMBER OF GROUPS WHOSE CONTENT SHOULD BE IGNORED.
                if ignore_groups is not None:
                    assert isinstance(
                        ignore_groups, list
                    ), "Ignore Groups wasn't properly transformed to an array<GUID>."
                    checks.append(metadata_object["author_guid"] not in ignore_groups)

                if ignore_tags is not None:
                    assert isinstance(ignore_tags, list), "Ignore Tags wasn't properly transformed to an array<GUID>."
                    checks.append(any(t["id"] not in ignore_tags for t in metadata_object["metadata_header"]["tags"]))

                if all(checks):
                    filtered.append(metadata_object)

                this_task.advance(step=1)

        if not filtered:
            log.info("[fg-warn]no stale content was found in your [fg-primary]ThoughtSpot[/] cluster")
            return 0

        with tracker["DUMP_DATA"] as this_task:
            if syncer is None:
                this_task.skip()

            else:
                d = [
                    models.ArchiverReport.validated_init(
                        type=metadata_object["type"],
                        guid=metadata_object["guid"],
                        modified=metadata_object["last_modified"],
                        reported_at=TODAY,
                        author_guid=metadata_object["author_guid"],
                        author=metadata_object["author_name"],
                        name=metadata_object["name"],
                        operation="IDENTIFY",
                    ).model_dump()
                    for metadata_object in filtered
                ]

                syncer.dump("archiver_report", data=d)

        with tracker["PREVIEW_DATA"]:
            t = Table(box=box.SIMPLE_HEAD, row_styles=("dim", ""), width=150)
            t.add_column("TYPE", justify="center", width=10)  # LIVEBOARD, ANSWER
            t.add_column("NAME", no_wrap=True)
            t.add_column("AUTHOR", width=20)
            t.add_column("MODIFIED", justify="right", width=12)  # NNN days ago

            for idx, row in enumerate(sorted(filtered, key=lambda row: row["last_modified"], reverse=True)):  # type: ignore
                if idx >= 15:
                    break

                t.add_row(
                    str(row["type"]).strip(),
                    str(row["name"]).strip(),
                    str(row["author_name"]).strip(),
                    f"{(TODAY - row['last_modified'].replace(tzinfo=dt.timezone.utc)).days} days ago",  # type: ignore
                )

            RICH_CONSOLE.print(Align.center(t))

        if dry_run:
            return 0

        with tracker["CONFIRM"] as this_task:
            if no_prompt:
                this_task.skip()

            else:
                this_task.description = "[fg-warn]Confirmation prompt"
                this_task.total = ONE_MINUTE = 60

                tracker.extra_renderable = lambda: Align.center(
                    console.Group(
                        Align.center(f"{len(filtered):,} '{tag_name}' objects found"),
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
                    this_task.description = "[fg-error]Denied[/] (no tagging done)"
                    return 0
                else:
                    this_task.description = f"[fg-success]Approved[/] (tagging {len(filtered):,})"

        with tracker["ARCHIVE_TAGGING"] as this_task:
            c = ts.api.tags_create(name=tag_name, color="#A020F0")  # ThoughtSpot Purple :~)
            _ = utils.run_sync(c)

            coros = []

            for metadata_object in filtered:
                c = ts.api.tags_assign(guid=metadata_object["guid"], tag=tag_name)
                coros.append(c)

            c = utils.bounded_gather(*coros, max_concurrent=15)
            d = utils.run_sync(c)

    return 0


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def untag(
    ctx: typer.Context,
    tag_name: str = typer.Option(_DEFAULT_TAG_NAME, "--tag", help="case sensitive name to tag stale objects with"),
) -> types.ExitCode:
    """Remove content with the identified --tag."""
    ts = ctx.obj.thoughtspot

    c = ts.api.tags_search()
    r = utils.run_sync(c)
    _ = r.json()

    try:
        tag = next(iter([{"metadata_guid": t["id"]} for t in _ if t["name"].casefold() == tag_name.casefold()]))
    except StopIteration:
        log.error(f"No tag found with the name '{tag_name}'")
        return 1

    c = ts.api.metadata_delete(guid=tag["metadata_guid"])
    r = utils.run_sync(c)

    if r.is_success:
        log.info(f"Removed tag '{tag_name}' from your objects.")
    else:
        log.error(f"Unable to remove tag '{tag_name}' from your objects.")
        log.debug(r.text)

    return 0


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def remove(
    ctx: typer.Context,
    tag_name: str = typer.Option(_DEFAULT_TAG_NAME, "--tag", help="case sensitive name to tag stale objects with"),
    dry_run: bool = typer.Option(False, "--dry-run", help="test your selection criteria (doesn't apply the tag)"),
    no_prompt: bool = typer.Option(False, "--no-prompt", help="disable the confirmation prompt"),
    syncer: Syncer = typer.Option(
        None,
        click_type=custom_types.Syncer(models=[models.ArchiverReport]),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    directory: pathlib.Path = typer.Option(
        None,
        metavar="DIRECTORY",
        help="folder/directory to export TML objects to",
        file_okay=False,
        rich_help_panel="TML Export Options",
    ),
    export_only: bool = typer.Option(
        False,
        "--export-only",
        help="export all tagged content, but don't remove it from ThoughtSpot",
        rich_help_panel="TML Export Options",
    ),
) -> types.ExitCode:
    """
    Remove objects from the ThoughtSpot platform.

    If the export --directory is specified, content identified with --tag will be saved
    as TML before being deleted from the ThoughtSpot platform.
    """
    ts = ctx.obj.thoughtspot

    TOOL_TASKS = [
        px.WorkTask(id="GATHER_METADATA", description="Fetching objects' Info"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {'nowhere' if syncer is None else syncer.name}"),
        px.WorkTask(id="PREVIEW_DATA", description=f"Sample [fg-secondary]{tag_name}[/] objects"),
        px.WorkTask(id="CONFIRM", description="Confirmation Prompt"),
        px.WorkTask(id="ARCHIVE_EXPORTING", description=f"Exporting [fg-secondary]{tag_name}[/] as TML"),
        px.WorkTask(id="ARCHIVE_DELETING", description=f"Deleting [fg-secondary]{tag_name}[/] objects"),
    ]

    TODAY = dt.datetime.now(tz=dt.timezone.utc)

    with px.WorkTracker("Removing Stale Objects", tasks=TOOL_TASKS) as tracker:
        with tracker["GATHER_METADATA"]:
            c = workflows.metadata.fetch_all(metadata_types=["ANSWER", "LIVEBOARD"], tag_identifiers=[tag_name], http=ts.api)  # noqa: E501
            d = utils.run_sync(c)

            filtered = [
                {
                    "guid": metadata_object["metadata_id"],
                    "name": metadata_object["metadata_name"],
                    "type": metadata_object["metadata_type"],
                    "author_guid": metadata_object["metadata_header"]["author"],
                    "author_name": metadata_object["metadata_header"]["authorName"],
                    "tags": metadata_object["metadata_header"]["tags"],
                    "last_modified": dt.datetime.fromtimestamp(
                        metadata_object["metadata_header"]["modified"] / 1000, tz=dt.timezone.utc
                    ),
                }
                for metadata_object in d
                if tag_name in (_["name"] for _ in metadata_object["metadata_header"]["tags"])
            ]

            if not filtered:
                log.info("[fg-warn]no stale content was found in your [fg-primary]ThoughtSpot[/] cluster")
                return 0

            TAG = next(
                iter(
                    _
                    for metadata_object in d
                    for _ in metadata_object["metadata_header"]["tags"]
                    if _["name"] == tag_name
                )
            )

        with tracker["DUMP_DATA"] as this_task:
            if syncer is None:
                this_task.skip()

            else:
                d = [
                    models.ArchiverReport.validated_init(
                        type=metadata_object["type"],
                        guid=metadata_object["guid"],
                        modified=metadata_object["last_modified"],
                        reported_at=TODAY,
                        author_guid=metadata_object["author_guid"],
                        author=metadata_object["author_name"],
                        name=metadata_object["name"],
                        operation="REMOVE",
                    ).model_dump()
                    for metadata_object in filtered
                ]

                syncer.dump("archiver_report", data=d)

        with tracker["PREVIEW_DATA"]:
            t = Table(box=box.SIMPLE_HEAD, row_styles=("dim", ""), width=150)
            t.add_column("TYPE", justify="center", width=10)  # LIVEBOARD, ANSWER
            t.add_column("NAME", no_wrap=True)
            t.add_column("AUTHOR", no_wrap=True, width=20)
            t.add_column("MODIFIED", justify="right", no_wrap=True, width=13)  # NNNN days ago

            for idx, row in enumerate(sorted(filtered, key=lambda row: row["last_modified"], reverse=True)):
                if idx >= 15:
                    break

                t.add_row(
                    str(row["type"]).strip(),
                    str(row["name"]).strip(),
                    str(row["author_name"]).strip(),
                    f"{(TODAY - row['last_modified'].replace(tzinfo=dt.timezone.utc)).days} days ago",
                )

            RICH_CONSOLE.print(Align.center(t))

        if dry_run:
            return 0

        with tracker["CONFIRM"] as this_task:
            if no_prompt:
                this_task.skip()

            else:
                this_task.description = "[fg-warn]Confirmation prompt"
                this_task.total = ONE_MINUTE = 60
                operation = "export" if export_only else "remov"  # Yes, intentionally spelled wrong.

                tracker.extra_renderable = lambda: Align.center(
                    console.Group(
                        Align.center(f"{len(filtered):,} '{tag_name}' objects will be {operation}ed"),
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
                    this_task.description = f"[fg-error]Denied[/] (no {operation}ing done)"
                    return 0
                else:
                    this_task.description = f"[fg-success]Approved[/] ({operation}ing {len(filtered):,})"

        with tracker["ARCHIVE_EXPORTING"] as this_task:
            if directory is None:
                this_task.skip()

            else:
                coros: list[Coroutine] = []

                for metadata_object in filtered:
                    c = workflows.metadata.tml_export(guid=metadata_object["guid"], edoc_format="YAML", directory=directory, http=ts.api)  # noqa: E501
                    coros.append(c)

                c = utils.bounded_gather(*coros, max_concurrent=4)
                d = utils.run_sync(c)

        if export_only:
            return 0

        with tracker["ARCHIVE_DELETING"]:
            coros: list[Coroutine] = []

            # DELETE THE TAG
            c = ts.api.metadata_delete(guid=TAG["id"])
            coros.append(c)

            for metadata_object in filtered:
                c = ts.api.metadata_delete(guid=metadata_object["guid"])
                coros.append(c)

            c = utils.bounded_gather(*reversed(coros), max_concurrent=15)
            d = utils.run_sync(c)

    return 0
