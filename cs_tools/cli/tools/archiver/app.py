import functools as ft
import pathlib
import logging
import random

import pendulum
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.layout import LiveTasks
from cs_tools.cli.input import ConfirmationPrompt
from cs_tools.cli.types import MultipleChoiceType, SyncerProtocolType
from cs_tools._compat import StrEnum
from cs_tools.cli.ux import rich_console
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import CSToolsApp
from cs_tools.errors import ContentDoesNotExist
from cs_tools.types import MetadataObjectType
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools import utils

from . import _extended_rest_api_v1
from . import layout

log = logging.getLogger(__name__)
ALL_BI_SERVER_HISTORY_IMPOSSIBLE_THRESHOLD_VALUE = 3650


class ContentType(StrEnum):
    answer = "answer"
    liveboard = "liveboard"
    all_user_content = "all"


app = CSToolsApp(
    help="""
    Manage stale answers and liveboards within your platform.

    As your platform grows, user-generated content will naturally grow. Sometimes, users
    will create content for temporary exploratory purposes and then abandon it for newer
    pursuits. Archiver enables you to identify, tag, export, and remove that potentially
    abandoned content.
    """,
)


@app.command(dependencies=[thoughtspot])
def identify(
    ctx: typer.Context,
    tag_name: str = Opt("INACTIVE", "--tag", help="case sensitive name to tag stale objects with"),
    dry_run: bool = Opt(False, "--dry-run", help="test your selection criteria (doesn't apply the tag)"),
    no_prompt: bool = Opt(False, "--no-prompt", help="disable the confirmation prompt"),
    content: ContentType = Opt(
        ContentType.all_user_content,
        help="type of content to mark for archival",
        rich_help_panel="Content Identification Criteria (applied with OR)"
    ),
    recent_activity: int = Opt(
        ALL_BI_SERVER_HISTORY_IMPOSSIBLE_THRESHOLD_VALUE,
        help=(
            "content without recent views will be [b green]selected[/] (exceeds days threshold) "
            # fake the default value in the CLI output
            "[dim]\[default: all TS: BI history][/]"
        ),
        show_default=False,
        rich_help_panel="Content Identification Criteria (applied with OR)"
    ),
    recent_modified: int = Opt(
        100,
        help="content without recent edits will be [b green]selected[/] (exceeds days threshold)",
        rich_help_panel="Content Identification Criteria (applied with OR)",
    ),
    only_groups: str = Opt(
        None,
        custom_type=MultipleChoiceType(),
        help="content not authored by users in these groups will be [b red]filtered[/], comma separated",
        rich_help_panel="Content Identification Criteria (applied with OR)",
    ),
    ignore_groups: str = Opt(
        None,
        custom_type=MultipleChoiceType(),
        help="content authored by users in these groups will be [b red]filtered[/], comma separated",
        rich_help_panel="Content Identification Criteria (applied with OR)",
    ),
    ignore_tags: str = Opt(
        None,
        custom_type=MultipleChoiceType(),
        help="content with this tag (case sensitive) will be [b red]filtered[/], comma separated",
        rich_help_panel="Content Identification Criteria (applied with OR)",
    ),
    report: DSyncer = Opt(
        None,
        custom_type=SyncerProtocolType(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
):
    # fmt: off
    """
    Identify content which can be archived.

    :police_car_light: [yellow]Content owned by system level accounts ([b blue]tsadmin[/], [b blue]system[/], [b blue]etc[/].) will be ignored.[/] :police_car_light:
    """
    # fmt: on
    if None not in (only_groups, ignore_groups):
        rich_console.log("[b red]Select either [b blue]--only-groups[/] or [b blue]--include-groups[/], but not both!")
        raise typer.Exit(1)

    ts = ctx.obj.thoughtspot

    tasks = [
        ("gather_ts_bi", "Getting content usage and activity statistics"),
        ("gather_supporting_filter_criteria", "Getting supporting metadata for content identification"),
        ("gather_metadata", "Getting existing content metadata"),
        ("syncer_report", f"Writing Archiver report{f' to {report.name}' if report is not None else ''}"),
        ("results_preview", f"Showing a sample of 25 items to tag with [b blue]{tag_name}"),
        ("confirmation_prompt", "Confirmation prompt"),
        ("tagging_content", "Tagging content in ThoughtSpot"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:

        with tasks["gather_ts_bi"]:
            ts_bi_rows = ts.search(
                f"[user action] != [user action].answer_unsaved [user action].{{null}} "
                f"[answer book guid] != [answer book guid].{{null}} "
                f"[timestamp].'last {recent_activity} days' "
                f"[timestamp].'today' "
                f"[answer book guid]",
                worksheet="TS: BI Server",
            )
            ts_bi_data = {row["Answer Book GUID"] for row in ts_bi_rows}

        with tasks["gather_supporting_filter_criteria"]:
            only_user_guids = [ts.group.users_in(group, is_directly_assigned=True) for group in (only_groups or [])]
            ignore_user_guids = [ts.group.users_in(group, is_directly_assigned=True) for group in (ignore_groups or [])]

        with tasks["gather_metadata"]:
            to_archive = []
            n_content_in_ts = 0

            for metadata_object in [*ts.answer.all(), *ts.liveboard.all()]:
                n_content_in_ts += 1
                checks = []

                # CHECK: TS: BI ACTIVITY -or- CONTENT MODIFICATION
                checks.append(
                    metadata_object["id"] not in ts_bi_data
                    or (metadata_object["modified"] / 1000) >= pendulum.now().subtract(days=recent_modified).timestamp()
                )

                # CHECK: AUTHOR IN APPROVED GROUPS
                if only_groups is not None:
                    checks.append(metadata_object["author"] in only_user_guids)

                # CHECK: AUTHOR NOT IN IGNORED GROUPS
                if ignore_groups is not None:
                    checks.append(metadata_object["author"] not in ignore_user_guids)

                # CHECK: METADATA DOES NOT CONTAIN ANY IGNORED TAG
                if ignore_tags is not None:
                    checks.append(not set(t["name"] for t in metadata_object["tags"]).intersection(ignore_tags))

                if all(checks):
                    to_archive.append(
                        {
                            "type": metadata_object["metadata_type"],
                            "guid": metadata_object["id"],
                            "modified": metadata_object["modified"],
                            "author_guid": metadata_object["author"],
                            "author": metadata_object.get("authorDisplayName", "{null}"),
                            "name": metadata_object["name"],
                        }
                    )

        if not to_archive:
            rich_console.log("[b yellow]no stale content was found in your [white]ThoughtSpot[/] cluster")
            raise typer.Exit(0)

        with tasks["results_preview"] as this_task:
            table = layout.build_table(
                        title=f"Content to tag with [b blue]{tag_name}",
                        caption=(
                            f"25 random items ({len(to_archive)} [b blue]{tag_name}[/] [dim]|[/] {n_content_in_ts} in "
                            f"ThoughtSpot)"
                        ),
                    )

            for row in random.sample(to_archive, k=min(25, len(to_archive))):
                table.add_row(
                    MetadataObjectType(row["type"]).name.title().replace("_", " "),
                    row["guid"],
                    pendulum.from_timestamp(row["modified"] / 1000, tz=ts.platform.timezone).strftime("%Y-%m-%d"),
                    row["author"],
                    row["name"],
                )

            tasks.draw = ft.partial(layout.combined_layout, tasks, original_layout=tasks.layout, new_layout=table)

        with tasks["syncer_report"] as this_task:
            if report is not None:
                to_archive = [{**_, "operation": "identify"} for _ in to_archive]
                report.dump("archiver_report", data=to_archive)
            else:
                this_task.skip()

        if dry_run:
            raise typer.Exit(-1)

        with tasks["confirmation_prompt"] as this_task:
            if no_prompt:
                this_task.skip()
            else:
                this_task.description = prompt = (
                    f":point_right: Continue with tagging {len(to_archive):,} objects? [b magenta](y/N)"
                )

                if not ConfirmationPrompt(prompt, console=rich_console).ask(with_prompt=False):
                    this_task.description = "Confirmation [b red]Denied[/] (no tagging performed)"
                    raise typer.Exit(0)

                this_task.description = "Confirmation [b green]Approved[/]"

        with tasks["tagging_content"]:
            tag_guid = ts.tag.get(tag_name, create_if_not_exists=True)
            to_tag_guids = []
            to_tag_types = []
            to_tag_names = []

            for content in to_archive:
                to_tag_guids.append(content["guid"])
                to_tag_types.append(content["type"])
                to_tag_names.append(tag_guid["id"])

            ts.api.metadata_assign_tag(metadata_guids=to_tag_guids, metadata_types=to_tag_types, tag_guids=to_tag_names)


@app.command(dependencies=[thoughtspot])
def revert(
    ctx: typer.Context,
    tag_name: str = Opt("INACTIVE", "--tag", help="case sensitive name to tag stale objects with"),
    dry_run: bool = Opt(False, "--dry-run", help="test your selection criteria (doesn't apply the tag)"),
    no_prompt: bool = Opt(False, "--no-prompt", help="disable the confirmation prompt"),
    delete_tag: bool = Opt(False, "--delete-tag", help="after untagging identified content, remove the tag itself"),
    report: DSyncer = Opt(
        None,
        custom_type=SyncerProtocolType(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
):
    """
    Remove content with the identified --tag.
    """
    ts = ctx.obj.thoughtspot

    tasks = [
        ("gather_metadata", f"Getting metadata tagged with [b blue]{tag_name}[/]"),
        ("syncer_report", f"Writing Archiver report{f' to {report.name}' if report is not None else ''}"),
        ("results_preview", f"Showing a sample of 25 items tagged with [b blue]{tag_name}"),
        ("confirmation_prompt", "Confirmation prompt"),
        ("untagging_content", f"Removing [b blue]{tag_name}[/] from content in ThoughtSpot"),
        ("deleting_tag", f"Removing the [b blue]{tag_name}[/] tag from ThoughtSpot"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:

        with tasks["gather_metadata"]:
            to_revert = []

            try:
                to_revert.extend(
                    {
                        "type": answer["metadata_type"],
                        "guid": answer["id"],
                        "modified": answer["modified"],
                        "author_guid": answer["author"],
                        "author": answer.get("authorDisplayName", "{null}"),
                        "name": answer["name"],
                    }
                    for answer in ts.answer.all(tags=[tag_name])
                )
            except ContentDoesNotExist:
                pass

            try:
                to_revert.extend(
                    {
                        "type": liveboard["metadata_type"],
                        "guid": liveboard["id"],
                        "modified": liveboard["modified"],
                        "author_guid": liveboard["author"],
                        "author": liveboard.get("authorDisplayName", "{null}"),
                        "name": liveboard["name"],
                    }
                    for liveboard in ts.liveboard.all(tags=[tag_name])
                )
            except ContentDoesNotExist:
                pass

        if not to_revert:
            rich_console.log(f"[b yellow]no [b blue]{tag_name}[/] content was found in [white]ThoughtSpot[/]")
            raise typer.Exit(0)

        with tasks["results_preview"] as this_task:
            table = layout.build_table(
                        title=f"Content to untag [b blue]{tag_name}",
                        caption=f"25 random items ({len(to_revert)} [b blue]{tag_name}[/] in ThoughtSpot)",
                    )

            for row in random.sample(to_revert, k=min(25, len(to_revert))):
                table.add_row(
                    MetadataObjectType(row["type"]).name.title().replace("_", " "),
                    row["guid"],
                    pendulum.from_timestamp(row["modified"] / 1000, tz=ts.platform.timezone).strftime("%Y-%m-%d"),
                    row["author"],
                    row["name"],
                )

            tasks.draw = ft.partial(layout.combined_layout, tasks, original_layout=tasks.layout, new_layout=table)

        with tasks["syncer_report"] as this_task:
            if report is not None:
                to_revert = [{**_, "operation": "revert"} for _ in to_revert]
                report.dump("archiver_report", data=to_revert)
            else:
                this_task.skip()

        if dry_run:
            raise typer.Exit(-1)

        with tasks["confirmation_prompt"] as this_task:
            if no_prompt:
                this_task.skip()
            else:
                this_task.description = prompt = (
                    f":point_right: Continue with untagging {len(to_revert):,} objects? [b magenta](y/N)"
                )

                if not ConfirmationPrompt(prompt, console=rich_console).ask(with_prompt=False):
                    this_task.description = "Confirmation [b red]Denied[/] (no tagging performed)"
                    raise typer.Exit(0)

                this_task.description = "Confirmation [b green]Approved[/]"

        with tasks["untagging_content"]:
            tag_guid = ts.tag.get(tag_name, create_if_not_exists=True)
            to_revert_guids = []
            to_revert_types = []
            to_revert_names = []

            for content in to_revert:
                to_revert_guids.append(content["guid"])
                to_revert_types.append(content["type"])
                to_revert_names.append(tag_guid["id"])

            ts.api.metadata_unassign_tag(
                metadata_guids=to_revert_guids,
                metadata_types=to_revert_types,
                tag_guids=to_revert_names,
            )

        with tasks["deleting_tag"] as this_task:
            if delete_tag:
                ts.tag.delete(tag_name=tag_name)
            else:
                this_task.skip()


@app.command(dependencies=[thoughtspot])
def remove(
    ctx: typer.Context,
    tag_name: str = Opt("INACTIVE", "--tag", help="case sensitive name to tag stale objects with"),
    dry_run: bool = Opt(False, "--dry-run", help="test your selection criteria (doesn't apply the tag)"),
    no_prompt: bool = Opt(False, "--no-prompt", help="disable the confirmation prompt"),
    delete_tag: bool = Opt(False, "--delete-tag", help="after deleting identified content, remove the tag itself"),
    report: DSyncer = Opt(
        None,
        custom_type=SyncerProtocolType(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    directory: pathlib.Path = Opt(
        None,
        metavar="DIRECTORY",
        help="folder/directory to export TML objects to",
        file_okay=False,
        rich_help_panel="TML Export Options",
    ),
    export_only: bool = Opt(
        False,
        "--export-only",
        help="export all tagged content, but don't remove it from",
        rich_help_panel="TML Export Options",
    ),
):
    """
    Remove objects from the ThoughtSpot platform.

    If the export --directory is specified, content identified with --tag will be saved
    as TML before being deleted from the ThoughtSpot platform.
    """
    ts = ctx.obj.thoughtspot

    tasks = [
        ("gather_metadata", f"Getting metadata tagged with [b blue]{tag_name}[/]"),
        ("syncer_report", f"Writing Archiver report{f' to {report.name}' if report is not None else ''}"),
        ("results_preview", f"Showing a sample of 25 items tagged with [b blue]{tag_name}"),
        ("confirmation_prompt", "Confirmation prompt"),
        ("export_content", f"Exporting content as TML{f' to {directory}' if directory is not None else ''}"),
        ("delete_content", f"Deleting [b blue]{tag_name}[/] content in ThoughtSpot"),
        ("deleting_tag", f"Removing the [b blue]{tag_name}[/] tag from ThoughtSpot"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:

        with tasks["gather_metadata"]:
            to_delete = []

            try:
                to_delete.extend(
                    {
                        "type": answer["metadata_type"],
                        "guid": answer["id"],
                        "modified": answer["modified"],
                        "author_guid": answer["author"],
                        "author": answer.get("authorDisplayName", "{null}"),
                        "name": answer["name"],
                    }
                    for answer in ts.answer.all(tags=[tag_name])
                )
            except ContentDoesNotExist:
                pass

            try:
                to_delete.extend(
                    {
                        "type": liveboard["metadata_type"],
                        "guid": liveboard["id"],
                        "modified": liveboard["modified"],
                        "author_guid": liveboard["author"],
                        "author": liveboard.get("authorDisplayName", "{null}"),
                        "name": liveboard["name"],
                    }
                    for liveboard in ts.liveboard.all(tags=[tag_name])
                )
            except ContentDoesNotExist:
                pass

        if not to_delete:
            rich_console.log(f"[b yellow]no [b blue]{tag_name}[/] content was found in [white]ThoughtSpot[/]")
            raise typer.Exit(0)

        with tasks["results_preview"] as this_task:
            table = layout.build_table(
                        title=f"Content to remove [b blue]{tag_name}[/]",
                        caption=f"25 random items ({len(to_delete)} [b blue]{tag_name}[/] in ThoughtSpot)",
                    )

            for row in random.sample(to_delete, k=min(25, len(to_delete))):
                table.add_row(
                    MetadataObjectType(row["type"]).name.title().replace("_", " "),
                    row["guid"],
                    pendulum.from_timestamp(row["modified"] / 1000, tz=ts.platform.timezone).strftime("%Y-%m-%d"),
                    row["author"],
                    row["name"],
                )

            tasks.draw = ft.partial(layout.combined_layout, tasks, original_layout=tasks.layout, new_layout=table)

        with tasks["syncer_report"] as this_task:
            if report is not None:
                to_delete = [{**_, "operation": "revert"} for _ in to_delete]
                report.dump("archiver_report", data=to_delete)
            else:
                this_task.skip()

        if dry_run:
            raise typer.Exit(-1)

        with tasks["confirmation_prompt"] as this_task:
            if no_prompt:
                this_task.skip()
            else:
                operation = "exporting" if export_only else "removing"
                this_task.description = prompt = (
                    f":point_right: Continue with {operation} {len(to_delete):,} objects? [b magenta](y/N)"
                )

                if not ConfirmationPrompt(prompt, console=rich_console).ask(with_prompt=False):
                    this_task.description = "Confirmation [b red]Denied[/] (no removal performed)"
                    raise typer.Exit(0)

                this_task.description = "Confirmation [b green]Approved[/]"

        with tasks["export_content"] as this_task:
            if directory is None:
                this_task.skip()
            else:
                for tml in ts.tml.to_export(guids=[content["guid"] for content in to_delete], iterator=True):
                    tml.dump(directory / f"{tml.guid}.{tml.tml_type_name}.tml")

        with tasks["delete_content"] as this_task:
            if export_only:
                this_task.skip()
            else:
                for unique_type in [c["type"] for c in to_delete]:
                    content = [content["guid"] for content in to_delete if content["type"] == unique_type]

                    for chunk in utils.chunks(content, n=50):
                        _extended_rest_api_v1.metadata_delete(
                            ts.api,
                            metadata_type=unique_type,
                            guids=list(chunk)
                        )

        with tasks["deleting_tag"] as this_task:
            if delete_tag:
                ts.tag.delete(tag_name=tag_name)
            else:
                this_task.skip()
