from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import collections
import logging
import re

from awesomeversion import AwesomeVersion
from httpx import HTTPStatusError
from rich.table import Table
from thoughtspot_tml import Connection
from thoughtspot_tml.exceptions import TMLError
from thoughtspot_tml.utils import determine_tml_type, disambiguate

from cs_tools.cli.ux import rich_console
from cs_tools.errors import CSToolsError, CSToolsCLIError
from cs_tools.types import GUID, TMLSupportedContent, TMLSupportedContentSubtype

from .tmlfs import ExportTMLFS

log = logging.getLogger(__name__)


@dataclass
class TMLExportResponse:
    guid: str
    metadata_object_type: str
    tml_type_name: str
    name: str
    status_code: str  # ERROR, WARNING, OK
    error_messages: Optional[list[str]] = None

    def __post_init__(self):
        self.error_messages = self._process_errors()

    def _process_errors(self) -> list[str]:
        if self.error_messages is None:
            return []
        return [_.strip() for _ in re.split("<br/>|\n", self.error_messages) if _.strip()]

    @property
    def is_success(self) -> bool:
        return self.status_code == "OK"


def export(ts, path, guids, tags, author, include_types, exclude_types, pattern, export_associated, org):
    if guids and (tags or author or include_types or exclude_types or pattern):
        raise CSToolsCLIError(
            title="GUID cannot be used with other filters.",
            reason="You can only specify GUIDs or a combination of other filters, such as author and tag.",
            mitigation=(
                "Modify your parameters to have GUIDS or author/tag. Note that tags and author can be used together."
            ),
        )

    if org is not None:
        ts.org.switch(org)

    tmlfs = ExportTMLFS(path, log)

    include_subtypes = None
    if include_types:
        include_types = [t.lower() for t in include_types]
        # have to do subtypes first since types is overwritten.
        include_subtypes = [
            str(TMLSupportedContentSubtype.from_friendly_type(t))
            for t in include_types
            if str(TMLSupportedContentSubtype.from_friendly_type(t))
        ]
        include_types = [str(TMLSupportedContent.from_friendly_type(t)) for t in include_types]

    exclude_subtypes = None
    if exclude_types:
        exclude_types = [t.lower() for t in exclude_types]
        # have to do subtypes first since types is overwritten.
        exclude_subtypes = [
            str(TMLSupportedContentSubtype.from_friendly_type(t))
            for t in exclude_types
            if str(TMLSupportedContentSubtype.from_friendly_type(t))
        ]
        exclude_types = [str(TMLSupportedContent.from_friendly_type(t)) for t in exclude_types]
    # some types you always want to exclude.
    exclude_types = (exclude_types or []) + ["LOGICAL_COLUMN", "LOGICAL_RELATIONSHIP", "USER", "USER_GROUP"]
    exclude_subtypes = exclude_subtypes or []

    log.debug(
        f"EXPORT args"
        f"\nguids={guids}"
        f"\ntags={tags}"
        f"\nauthor={author}"
        f"\npattern={pattern}"
        f"\ninclude_types={include_types}"
        f"\ninclude_subtypes={include_subtypes}"
        f"\nexclude_types={exclude_types}"
        f"\nexclude_subtypes={exclude_subtypes}"
    )

    # Scenarios to support
    # GUID/filters - download the content and save
    # With associated - download content with associated and save
    # With fqns - download content with associated, map FQNs, save content specified (original or with FQNs)

    if guids:
        export_objects = ts.metadata.get(guids)
    else:
        export_objects = ts.metadata.find(
            tags=tags,
            author=author,
            pattern=pattern,
            include_types=include_types,
            include_subtypes=include_subtypes,
            exclude_types=exclude_types,
            exclude_subtypes=exclude_subtypes,
        )

    results: list[TMLExportResponse] = []

    for content in export_objects:
        guid = content["id"]
        metadata_type = content["metadata_type"]
        with_ = "with" if export_associated else "without"

        with rich_console.status(f"[b green]exporting {guid} ({metadata_type}) {with_} associated content.[/]"):
            try:
                if metadata_type == TMLSupportedContent.connection:
                    r = _download_connection(ts=ts, tmlfs=tmlfs, guid=guid)
                else:
                    r = _download_tml(ts=ts, tmlfs=tmlfs, guid=guid, export_associated=export_associated)

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

    if results:
        _show_results_as_table(results=results)
    else:
        log.warning("No TML found matching the input conditions")


def _download_connection(ts, tmlfs: ExportTMLFS, guid: GUID) -> list[TMLExportResponse]:
    """
    Download a connection.

    Connections aren't supported by TML yet.
    """
    r = ts.api.v1.connection_export(guid=guid)
    tml = Connection.loads(r.text)
    tml.guid = guid

    r = TMLExportResponse(
        guid=guid,
        metadata_object_type="DATA_SOURCE",
        tml_type_name="connection",
        name=tml.name,
        status_code="OK",
        error_messages=None,
    )

    try:
        tmlfs.write_tml(tml=tml)
    except OSError:
        r.status_code = "ERROR"
        r.error_messages = [f"Error writing to file: {tml.name}"]

    return [r]


def _download_tml(ts, tmlfs: ExportTMLFS, guid: GUID, export_associated: bool) -> list[TMLExportResponse]:
    # DEV NOTE: @billdback 2023/01/14 , we'll only download one parent at a time to account for FQN mapping
    r = ts.api.v1.metadata_tml_export(
        export_guids=[guid],
        format_type="YAML",
        export_associated=export_associated,
        export_fqn=True,
    )

    results: list[TMLExportResponse] = []
    tml_objects = []

    for content in r.json()["object"]:
        info = content["info"]

        r = TMLExportResponse(
            guid=info["id"],
            metadata_object_type=TMLSupportedContent[info["type"]],
            tml_type_name=info["type"],
            name=info["name"],
            status_code=info["status"]["status_code"],
            error_messages=info["status"].get("error_message", None),
        )

        results.append(r)

        if not r.is_success:
            log.warning(f"[b red]unable to get {r.name}: {r.status_code}")

        else:
            log.info(f"{content['info']['filename']} (Downloaded)")

            try:
                tml_type = determine_tml_type(info=info)
                tml = tml_type.loads(tml_document=content["edoc"])
                tml_objects.append(tml)

            except TMLError as tml_error:
                log.warning(f"[b red]Unable to parse '[b blue]{r.name}.{r.tml_type_name}.tml[/]' to a TML object.")
                log.error(tml_error, exc_info=True)
                log.debug(f"decode error for edoc:\n{content['edoc']}")
                r.status_code = "WARNING"
                r.error_messages = ["Unable to parse to TML object."]

    # .export_fqn NEW in 8.7.0, here's the backwards compat
    if ts.session_context.thoughtspot.version < AwesomeVersion("8.7.0"):
        for tml in tml_objects:
            parents = ts.metadata.table_references(tml.guid, tml_type=tml.tml_type_name)
            guid_name_map = {parent.parent_guid: parent.parent_name for parent in parents}
            counter = collections.Counter(guid_name_map.values())
            more_than_one = {name: count for name, count in counter.items() if count > 1}

            if more_than_one:
                log.warning(
                    f"multiple objects found with names: [b blue]{', '.join(more_than_one.keys())}[/], disambiguation "
                    f"will be incomplete"
                )

            disambiguate(tml, guid_mapping=guid_name_map)

    for tml in tml_objects:
        tmlfs.write_tml(tml=tml)

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

    log.info("Export Results:\n")
    for r in sorted(results, key=lambda r: r.status_code):
        log.info(f"{r.status_code} {r.guid} {r.name} {' '.join(r.error_messages)}")
        table.add_row(r.status_code, r.guid, r.name, " ".join(r.error_messages))

    rich_console.print(table)
