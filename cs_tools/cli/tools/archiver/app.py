from typing import Any, Dict, List, Tuple
import logging
import pathlib

from typer import Argument as A_, Option as O_  # noqa
import pendulum
import click
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import CommaSeparatedValuesType, SyncerProtocolType
from cs_tools.cli.util import base64_to_file
from cs_tools.cli.ux import console, CSToolsApp, CSToolsArgument as Arg, CSToolsOption as Opt
from cs_tools.errors import ContentDoesNotExist

from .enums import ContentType, UserActions
from .util import DataTable


log = logging.getLogger(__name__)


def _get_content(ts, *, tags) -> Tuple[List[Dict[str, Any]]]:
    try:
        answers = [{"content_type": "answer", **_} for _ in ts.answer.all(tags=tags)]
    except ContentDoesNotExist:
        answers = []

    try:
        liveboard = [{"content_type": "liveboard", **_} for _ in ts.liveboard.all(tags=tags)]
    except ContentDoesNotExist:
        liveboard = []

    return answers, liveboard


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
    ctx: click.Context,
    tag_name: str = Opt("INACTIVE", "--tag", help="tag name to use for labeling objects to archive (case sensitive)"),
    content: ContentType = Opt("all", help="type of content to archive"),
    recent_activity: int = Opt(
        3650, help="days to IGNORE for content viewed or access [default: all history]", show_default=False
    ),
    recent_modified: int = Opt(
        100,
        help="days to IGNORE for content created or modified",
    ),
    ignore_tag: List[str] = Opt(
        None,
        help="tagged content to ignore (case sensitive), can be specified multiple times",
        callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
    ),
    dry_run: bool = Opt(
        False,
        "--dry-run",
        help="test your selection criteria, doesn't apply tags",
        show_default=False,
    ),
    no_prompt: bool = Opt(False, "--no-prompt", help="disable the confirmation prompt", show_default=False),
    report: str = Opt(
        None,
        metavar="protocol://DEFINITION.toml",
        help="generates a list of content to be archived, utilizes protocol syntax",
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx),
    ),
):
    """
    Identify objects which objects can be archived.

    [yellow]Identification criteria will skip content owned by "System User" (system)
    and "Administrator" (tsadmin)[/]

    ThoughtSpot stores usage activity (default: 6 months of interactions) by user in the
    platform. If a user views, edits, or creates an Answer or Liveboard, ThoughtSpot
    knows about it. This can be used as a proxy to understanding what content is
    actively being used.
    """
    ts = ctx.obj.thoughtspot
    tz = ts.platform.tz
    actions = UserActions.strigified(sep="', '", context=content)

    with console.status("[bold green]retrieving objects usage..[/]"):
        data = ts.search(
            f"[user action] = '{actions}' "
            f"[timestamp].'last {recent_activity} days' "
            r"[timestamp].'today' "
            r"[answer book guid]",
            worksheet="TS: BI Server",
        )

    # SELECTION LOGIC
    # 1. Get all existing GUIDs in the platform.  (metadata/list)
    # 2. Filter out recently modified GUIDs.      (object.created , object.modified)
    # 3. Filter out recently accessed GUIDs.      (TS: BI Server)
    #
    content_in_platform = 0
    to_archive = []
    seen_recently = set(obj["Answer Book GUID"] for obj in data)
    recently = pendulum.now(tz=tz).subtract(days=recent_modified)
    tags_to_ignore = [t.casefold() for t in ignore_tag]

    if content.value in ("all", "answer"):
        with console.status("[bold green]retrieving existing answers..[/]"):
            for answer in ts.answer.all():
                content_in_platform += 1
                add = pendulum.from_timestamp(answer["created"] / 1000, tz=tz)
                mod = pendulum.from_timestamp(answer["modified"] / 1000, tz=tz)
                tag = [t["name"].casefold() for t in answer["tags"]]

                if (
                    add >= recently
                    or mod >= recently
                    or set(tag).intersection(tags_to_ignore)
                    or answer["id"] in seen_recently
                ):
                    continue

                to_archive.append(
                    {
                        "content_type": "answer",
                        "guid": answer["id"],
                        "name": answer["name"],
                        "created_at": add.diff_for_humans(),
                        "modified_at": mod.diff_for_humans(),
                        "author": answer.get("authorName"),
                    }
                )

    if content.value in ("all", "liveboard"):
        with console.status("[bold green]retrieving existing liveboards..[/]"):
            for liveboard in ts.liveboard.all():
                content_in_platform += 1
                add = pendulum.from_timestamp(liveboard["created"] / 1000, tz=tz)
                mod = pendulum.from_timestamp(liveboard["modified"] / 1000, tz=tz)
                tag = [t["name"].casefold() for t in liveboard["tags"]]

                if (
                    add >= recently
                    or mod >= recently
                    or set(tag).intersection(tags_to_ignore)
                    or liveboard["id"] in seen_recently
                ):
                    continue

                to_archive.append(
                    {
                        "content_type": "liveboard",
                        "guid": liveboard["id"],
                        "name": liveboard["name"],
                        "created_at": add.diff_for_humans(),
                        "modified_at": mod.diff_for_humans(),
                        "author": liveboard.get("authorName"),
                    }
                )

    if not to_archive:
        console.log("no stale content found")
        raise typer.Exit()

    table_kw = {
        "title": f"[green]Archive Results[/]: Tagging content with [cyan]{tag_name}",
        "caption": f"{len(to_archive)} items tagged ({content_in_platform} in cluster)",
    }

    console.log(DataTable(to_archive, **table_kw), justify="center")

    if report is not None:
        to_archive = [{**_, "operation": "identify"} for _ in to_archive]
        report.dump("archiver_report", data=to_archive)

    if dry_run:
        raise typer.Exit(-1)

    tag = ts.tag.get(tag_name, create_if_not_exists=True)
    contents = {"answer": [], "liveboard": []}
    [contents[c["content_type"]].append(c["guid"]) for c in to_archive]

    # PROMPT FOR INPUT
    if not no_prompt:
        typer.confirm(f"\nWould you like to continue with tagging {len(to_archive)} objects?", abort=True)

    if contents["answer"]:
        ts.api.metadata.assigntag(
            id=contents["answer"],
            type=["QUESTION_ANSWER_BOOK"] * len(contents["answer"]),
            tagid=[tag["id"]] * len(contents["answer"]),
        )

    if contents["liveboard"]:
        ts.api.metadata.assigntag(
            id=contents["liveboard"],
            type=["PINBOARD_ANSWER_BOOK"] * len(contents["liveboard"]),
            tagid=[tag["id"]] * len(contents["liveboard"]),
        )


@app.command(dependencies=[thoughtspot])
def revert(
    ctx: typer.Context,
    tag_name: str = Opt("INACTIVE", "--tag", help="tag name to revert on labeled content (case sensitive)"),
    delete_tag: bool = Opt(
        False, "--delete-tag", help="remove the tag itself, after untagging identified content", show_default=False
    ),
    dry_run: bool = Opt(
        False, "--dry-run", show_default=False, help="test your selection criteria, doesn't revert tags"
    ),
    no_prompt: bool = Opt(False, "--no-prompt", show_default=False, help="disable the confirmation prompt"),
    report: str = Opt(
        None,
        metavar="protocol://DEFINITION.toml",
        help="generates a list of content to be reverted, utilizes protocol syntax",
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx),
    ),
):
    """
    Remove objects from the temporary archive.
    """
    ts = ctx.obj.thoughtspot
    tz = ts.platform.tz

    to_unarchive = []
    answers, liveboards = _get_content(ts, tags=tag_name)

    for content in (*answers, *liveboards):
        add = pendulum.from_timestamp(content["created"] / 1000, tz=tz)
        mod = pendulum.from_timestamp(content["modified"] / 1000, tz=tz)
        to_unarchive.append(
            {
                "content_type": content["content_type"],
                "guid": content["id"],
                "name": content["name"],
                "created_at": add.diff_for_humans(),
                "modified_at": mod.diff_for_humans(),
                "author": content.get("authorName"),
            }
        )

    if not to_unarchive:
        console.log(f"no content found with the tag '{tag_name}'")
        raise typer.Exit()

    table_kw = {
        "title": f"[green]Unarchive Results[/]: Untagging content with [cyan]{tag_name}",
        "caption": f"Total of {len(to_unarchive)} items tagged..",
    }

    console.log(DataTable(to_unarchive, **table_kw), justify="center")

    if report is not None:
        to_unarchive = [{**_, "operation": "revert"} for _ in to_unarchive]
        report.dump("archiver_report", data=to_unarchive)

    if dry_run:
        raise typer.Exit()

    tag = ts.tag.get(tag_name)

    contents = {"answer": [], "liveboard": []}
    [contents[c["content_type"]].append(c["guid"]) for c in to_unarchive]

    # PROMPT FOR INPUT
    if not no_prompt:
        typer.confirm(f"\nWould you like to continue with untagging {len(to_unarchive)} objects?", abort=True)

    if contents["answer"]:
        ts.api.metadata.unassigntag(
            id=contents["answer"],
            type=["QUESTION_ANSWER_BOOK"] * len(contents["answer"]),
            tagid=[tag["id"]] * len(contents["answer"]),
        )

    if contents["liveboard"]:
        ts.api.metadata.unassigntag(
            id=contents["liveboard"],
            type=["PINBOARD_ANSWER_BOOK"] * len(contents["liveboard"]),
            tagid=[tag["id"]] * len(contents["liveboard"]),
        )

    if delete_tag:
        ts.tag.delete(tag["name"])


@app.command(dependencies=[thoughtspot])
def remove(
    ctx: typer.Context,
    tag_name: str = Opt("INACTIVE", "--tag", help="tag name to use to remove objects (case sensitive)"),
    export_tml: pathlib.Path = Opt(
        None,
        metavar="FILE.zip",
        dir_okay=False,
        resolve_path=True,
        help="if set, path to export tagged objects as a zipfile",
    ),
    delete_tag: bool = Opt(
        False,
        "--delete-tag",
        show_default=False,
        help="remove the tag itself, after deleting identified content",
    ),
    export_only: bool = Opt(
        False,
        "--export-only",
        show_default=False,
        help="export all tagged content, but do not remove it from that platform",
    ),
    dry_run: bool = Opt(
        False, "--dry-run", show_default=False, help="test your selection criteria, doesn't delete content"
    ),
    no_prompt: bool = Opt(False, "--no-prompt", show_default=False, help="disable the confirmation prompt"),
    report: str = Opt(
        None,
        metavar="protocol://DEFINITION.toml",
        help="generates a list of content to be reverted, utilizes protocol syntax",
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx),
    ),
):
    """
    Remove objects from the ThoughtSpot platform.
    """
    ts = ctx.obj.thoughtspot
    tz = ts.platform.tz

    if export_tml is not None:
        if not export_tml.as_posix().endswith("zip"):
            console.print(f"[error]Path must be a valid zipfile! Got: [blue]{export_tml}")
            raise typer.Exit(-1)

        if export_tml.exists():
            console.print(f"[yellow]Zipfile [blue]{export_tml}[/] already exists!")
            typer.confirm("Would you like to overwrite it?", abort=True)

    to_unarchive = []
    answers, liveboards = _get_content(ts, tags=tag_name)

    for content in (*answers, *liveboards):
        add = pendulum.from_timestamp(content["created"] / 1000, tz=tz)
        mod = pendulum.from_timestamp(content["modified"] / 1000, tz=tz)
        to_unarchive.append(
            {
                "content_type": content["content_type"],
                "guid": content["id"],
                "name": content["name"],
                "created_at": add.diff_for_humans(),
                "modified_at": mod.diff_for_humans(),
                "author": content.get("authorName"),
            }
        )

    if not to_unarchive:
        console.log(f"no content found with the tag [blue]{tag_name}")
        raise typer.Exit()

    table_kw = {
        "title": (
            "[green]Remove Results[/]: Removing"
            + ("" if export_tml is None else " and exporting")
            + f" content with [cyan]{tag_name}"
        ),
        "caption": f"Total of {len(to_unarchive)} items tagged..",
    }

    console.log(DataTable(to_unarchive, **table_kw), justify="center")

    if report is not None:
        to_unarchive = [{**_, "operation": "remove"} for _ in to_unarchive]
        report.dump("archiver_report", data=to_unarchive)

    if dry_run:
        raise typer.Exit()

    tag = ts.tag.get(tag_name)

    contents = {"answer": [], "liveboard": []}
    [contents[c["content_type"]].append(c["guid"]) for c in to_unarchive]

    # PROMPT FOR INPUT
    if not no_prompt:
        if export_only:
            op = "exporting"
        elif export_tml:
            op = "exporting and removing"
        else:
            op = "removing"

        typer.confirm(f"\nWould you like to continue with {op} {len(to_unarchive)} objects?", abort=True)

    if export_tml is not None:
        r = ts.api._metadata.edoc_export_epack(
            request={
                "object": [
                    *[{"id": id, "type": "QUESTION_ANSWER_BOOK"} for id in contents["answer"]],
                    *[{"id": id, "type": "PINBOARD_ANSWER_BOOK"} for id in contents["liveboard"]],
                ],
                "export_dependencies": False,
            }
        )

        if not r.json().get("zip_file"):
            console.log(
                "[error]attempted to export TML, but the API response failed, please "
                "re-run the command with --verbose flag to capture more log details"
            )
            raise typer.Exit(-1)

        base64_to_file(r.json()["zip_file"], filepath=export_tml)

    if export_only:
        raise typer.Exit()

    if answers:
        ts.api._metadata.delete(id=contents["answer"], type="QUESTION_ANSWER_BOOK")

    if liveboards:
        ts.api._metadata.delete(id=contents["liveboard"], type="PINBOARD_ANSWER_BOOK")

    if delete_tag:
        ts.tag.delete(tag["name"])
