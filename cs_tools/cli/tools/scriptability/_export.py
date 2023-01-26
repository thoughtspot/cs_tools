"""
This file contains the methods to execute the 'scriptability export' command.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
import collections
import pathlib
import logging
import re

from thoughtspot_tml.exceptions import TMLError
from thoughtspot_tml.utils import determine_tml_type, disambiguate
from thoughtspot_tml import Connection
from awesomeversion import AwesomeVersion
from rich.table import Table
from cs_tools.cli.ux import CSToolsArgument as Arg
from cs_tools.cli.ux import CSToolsOption as Opt
from httpx import HTTPStatusError
import typer

from cs_tools.cli.types import CommaSeparatedValuesType
from cs_tools.errors import CSToolsError
from cs_tools.cli.ux import rich_console
from cs_tools.types import TMLSupportedContent, GUID

from .util import strip_blanks

log = logging.getLogger(__name__)


@dataclass
class TMLExportResponse:
    guid: str
    metadata_object_type: str
    tml_type_name: str
    name: str
    status_code: str  # ERROR, WARNING, OK
    error_messages: List[str] = None

    def __post_init__(self):
        self.error_messages = self._process_errors()

    def _process_errors(self) -> List[str]:
        if self.error_messages is None:
            return []
        return [_.strip() for _ in re.split("<br/>|\n", self.error_messages) if _.strip()]

    @property
    def is_success(self) -> bool:
        return self.status_code == "OK"


def export(
    ctx: typer.Context,
    path: pathlib.Path = Arg(  # may not want to use
        ..., help="path to save data set to", dir_okay=False, resolve_path=True
    ),
    tags: List[str] = Opt(
        None,
        metavar="TAGS",
        callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
        help="comma separated list of tags to export",
    ),
    guids: list[GUID] = Opt(
        None,
        metavar="GUIDS",
        callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
        help="comma separated list of GUIDs to export",
    ),
    author: str = Opt(None, metavar="USERNAME", help="username that is the author of the content to download"),
    pattern: str = Opt(None, metavar="PATTERN", help=r"pattern for name with % as a wildcard"),
    include_types: List[str] = Opt(
        None,
        metavar="CONTENTTYPES",
        callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
        help="list of types to include: answer, liveboard, view, sqlview, table, connection",
    ),
    exclude_types: List[str] = Opt(
        None,
        metavar="CONTENTTYPES",
        callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
        help="list of types to exclude (overrides include): answer, liveboard, view, sqlview, table, connection",
    ),
    export_associated: bool = Opt(False, help="if specified, also export related content"),
    org: str = Opt(None, help="name or id of the org to export from", hidden=True),
):
    """
    Exports TML as YAML from ThoughtSpot.

    There are different parameters that can impact content to download. At least one
    needs to be specified.

    - GUIDs: only content with the specific GUIDs will be downloaded.
    - filters, e.g tags, author, pattern, include_types, exclude_types.

    If you specify GUIDs then you can't use any filters.

    Filters are applied in AND fashion - only items that match all filters will be
    exported. For example, if you export for the "finance" tag and author "user123",
    then only content owned by that user with the "finance" tag will be exported.
    """
    if guids and (tags or author or include_types or exclude_types or pattern):
        raise CSToolsError(
            error="GUID cannot be used with other filters.",
            reason="You can only specify GUIDs or a combination of other filters, such as author and tag.",
            mitigation=(
                "Modify your parameters to have GUIDS or author/tag. Note that tags and author can be used together."
            ),
        )

    # TODO: ensure this logic is captured in the CLI parsing above....
    # do some basic cleanup to make sure we don't have extra spaces or case issues.
    export_ids = strip_blanks(guids)
    tags = strip_blanks(tags)
    include_types = [_.strip().lower() for _ in include_types]
    exclude_types = [_.strip().lower() for _ in exclude_types + ["USER", "USER_GROUP"]]
    author = author.strip() if author else None
    #

    ts = ctx.obj.thoughtspot

    if org is not None:
        ts.org.switch(org)

    # Scenarios to support
    # GUID/filters - download the content and save
    # With associated - download content with associated and save
    # With fqns - download content with associated, map FQNs, save content specified (original or with FQNs)

    if export_ids:
        export_objects = ts.metadata.get(export_ids)
    else:
        export_objects = ts.metadata.find(
            tags=tags,
            author=author,
            pattern=pattern,
            include_types=[TMLSupportedContent[friendly] for friendly in include_types],
            exclude_types=[TMLSupportedContent[friendly] for friendly in exclude_types],
        )

    results: list[TMLExportResponse] = []

    for content in export_objects:
        guid = content["id"]
        metadata_type = content["metadata_type"]
        with_ = "with" if export_associated else "without"

        with rich_console.status(f"[b green]exporting {guid} ({metadata_type}) {with_} associated content.[/]"):

            try:
                if metadata_type == TMLSupportedContent.connection:
                    r = _download_connection(ts=ts, path=path, guid=guid)
                else:
                    r = _download_tml(ts=ts, path=path, guid=guid, export_associated=export_associated)

                results.extend(r)

            # Sometimes we get a 400 error on the content. Need to just log an error and continue.
            except HTTPStatusError as e:
                log.error(f"error exporting TML for GUID '[b blue]{guid}[/]'. check logs for more details..")
                log.debug(e, exc_info=True)
                results.append(
                    TMLExportResponse(
                        guid=guid,
                        metadata_object_type=metadata_type,
                        tml_type_name="UNKNOWN",
                        name="UNKNOWN",
                        status_code="ERROR",
                        error_messages=str(e),
                    )
                )

    _show_results_as_table(results=results)


def _download_connection(ts, directory: pathlib.Path, guid: GUID) -> list[TMLExportResponse]:
    """
    Download a connection.

    Connections aren't supported by TML yet.
    """
    r = ts.api.connection_export(guid=guid)
    tml = Connection.loads(r.text)

    r = TMLExportResponse(
        guid=guid,
        metadata_object_type="DATA_SOURCE",
        tml_type_name="connection",
        name=tml.name,
        status_code="OK",
        error_messages=None,
    )

    try:
        tml.dump(directory / f"{guid}.connection.tml")
    except IOError:
        r.status_code = "ERROR"
        r.error_messages = [f"Error writing to file: {tml.name}"]

    return [r]


def _download_tml(ts, directory: pathlib.Path, guid: GUID, export_associated: bool) -> list[TMLExportResponse]:

    # DEV NOTE: @billdback 2023/01/14 , we'll only download one parent at a time to account for FQN mapping
    r = ts.api.metadata_tml_export(
        export_guids=[guid],
        format_type="YAML",
        export_associated=export_associated,
        export_fqn=True,
    )

    results: list[TMLExportResponse] = []

    if r.json().get("object", []):
        return results

    tml_objects = []

    for content in r.json()["object"]:
        info = content["info"]

        r = TMLExportResponse(
            guid=info["id"],
            metadata_object_type=TMLSupportedContent.from_child_type(info["type"]).to_metadata_object_type(),
            tml_type_name=info["type"],
            name=info["name"],
            status_code=info["status"]["status_code"],
            error_messages=info["status"].get("error_message", None),
        )

        if not r.is_success:
            log.warning(f"[b red]unable to get {r.name}: {r.status_code}")
            results.append(r)

        else:
            log.info(f"{content['info']['filename']} (Downloaded)")

            try:
                tml_type = determine_tml_type(info=info)
                tml = tml_type.loads(tml_document=content["edoc"])
                tml_objects.append(tml)

            except TMLError:
                log.warning(f"[b red]Unable to parse '[b blue]{r.name}.{r.tml_type_name}.tml[/]' to a TML object.")
                log.debug(f"decode error for edoc:\n{content['edoc']}")
                r.status_code = "WARNING"
                r.error_messages = ["Unable to parse to TML object."]

    # .export_fqn NEW in 8.7.0, here's the backwards compat
    if AwesomeVersion(ts.platform.version) < AwesomeVersion("8.7.0"):
        for tml in tml_objects:
            guid_name_map = ts.metadata.table_references(tml.guid, tml_type=tml.tml_type_name)
            counter = collections.Counter(guid_name_map.values())
            more_than_one = {name: count for name, count in counter.items() if count > 1}

            if more_than_one:
                log.warning(
                    f"multiple objects found with names: [b blue]{', '.join(more_than_one.keys())}[/], disambiguation "
                    f"will be incomplete"
                )

            disambiguate(tml, guid_mapping=guid_name_map)

    for tml in tml_objects:
        tml.dump(directory / f"{tml.guid}.{tml.tml_type_name}.tml")

    return results


def _show_results_as_table(results: list[TMLExportResponse]) -> None:
    """
    Writes a pretty results table to the rich_console.
    """
    table = Table(title="Export Results", width=150)

    table.add_column("Status", justify="center", width=10)  # 4 + length of literal: status
    table.add_column("GUID", justify="center", width=40)  # 4 + length of a guid
    table.add_column("Name", no_wrap=True, width=40)  # (150 - above) , 40% of available space
    table.add_column("Description", no_wrap=True, width=60)  # (150 - above) , 60% of available space

    for r in sorted(results, key=lambda r: r.status_code):
        table.add_row(r.status_code, r.guid, r.name, " ".join(r.error_messages))

    rich_console.print(table)
