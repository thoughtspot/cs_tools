"""
This file contains the methods to execute the 'scriptability import' command.
"""
from __future__ import annotations

import logging
import pathlib
import re
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

from awesomeversion import AwesomeVersion
from httpx import HTTPStatusError
from rich.align import Align
from rich.table import Table
from thoughtspot_tml import Connection
from thoughtspot_tml._tml import TML
from thoughtspot_tml.exceptions import TMLDecodeError
from thoughtspot_tml.utils import _recursive_scan

from cs_tools.cli.tools.scriptability.util import GUIDMapping
from cs_tools.cli.ux import rich_console
from cs_tools.errors import CSToolsError
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.types import GUID, MetadataObjectType, ShareModeAccessLevel, TMLImportPolicy, TMLSupportedContent, TMLSupportedContentSubtype
from cs_tools.utils import chunks
from ._mapping import show_mapping_details
from .tmlfs import ImportTMLFS, TMLType

log = logging.getLogger(__name__)


@dataclass
class TMLImportResponse:
    guid: str
    metadata_object_type: str
    tml_type_name: str
    name: str
    status_code: str  # ERROR, WARNING, OK
    error_messages: Optional[List[str]] = None

    def __post_init__(self):
        self.error_messages = self._process_errors()

    def _process_errors(self) -> List[str]:
        res = []
        if self.error_messages:
            try:  # most, but not all errors are in this format
                res = [_.strip() for _ in re.split("<br/>|\n", self.error_messages) if _.strip()]
            except re.error:
                res = self.error_messages
            except TypeError:
                res = self.error_messages
        return res

    @property
    def is_success(self) -> bool:
        return self.status_code == "OK"

    @property
    def is_error(self) -> bool:
        return self.status_code == "ERROR"


def to_import(
        ts: ThoughtSpot,
        path: pathlib.Path,  # root of the TML file system.
        guid: GUID,  # GUID for the TML to import if only one is being imported.  Assumes dependencies are met, so
        # this is usually an update.
        import_policy: TMLImportPolicy,  # Import policy to use.
        force_create: bool,  # Force creation of new content.
        source: str,  # Source of the TML being imported.  Used for mapping.
        dest: str,  # Destination of the TML being imported.  Used for mapping.
        tags: Optional[List[str]],  # Tags to apply to imported content.
        share_with: Optional[List[str]],  # Users and groups to share with.
        org: str,  # Org to import into.
        include_types: Optional[List[str]],  # Types of TML to import.
        exclude_types: Optional[List[str]],  # Types of TML to exclude from import.
        show_mapping: bool,  # Show the mapping file details.
):
    """
    Import TML from a file or directory into ThoughtSpot.

    \b
    cs_tools depends on thoughtspot_tml. The GUID file is produced from
    thoughtspot_tml and requires a specific format. For further information on the
    GUID File, see

       https://github.com/thoughtspot/thoughtspot_tml/tree/v2_0_release#environmentguidmapper
    """
    all_responses: List[TMLImportResponse] = []

    # ideally this will be moved to the config file
    if org is not None:
        ts.org.switch(org)

    # Check the parameters to make sure they make sense together.  If not, then raise an exception.
    _check_parameters(path=path, source=source, dest=dest, guid=guid,
                      include_types=include_types, exclude_types=exclude_types)

    tmlfs = ImportTMLFS(path, log)

    # if a source and destination were specified, then use the mapping file.  If not, use the`name` from the config.
    mapping_file: Optional[GUIDMapping] = None
    if source and dest:
        mapping_file = tmlfs.read_mapping_file(source=source, dest=dest)
    else:
        mapping_file = tmlfs.read_mapping_file(source=ts.config.name, dest=ts.config.name)

    if guid:
        all_responses.extend(_load_from_file(ts=ts, tmlfs=tmlfs, guid=guid, import_policy=import_policy,
                                             force_create=force_create, mapping_file=mapping_file))
    else:
        all_responses.extend(
            _load_from_dir(ts=ts, tmlfs=tmlfs, import_policy=import_policy, force_create=force_create,
                           mapping_file=mapping_file, include_types=include_types, exclude_types=exclude_types)
        )

    mapping_file.save()  # save any changes to the mapping file.

    # show the results to the user.
    _show_results_as_table(results=all_responses)

    if _some_tml_updated(import_policy, all_responses):  # only update and share if there were actual updates.
        if tags:
            try:
                _add_tags(ts, [r for r in all_responses if not r.is_error], tags)
            except HTTPStatusError as e:
                log.error(f"Unable to add tags: {e.response.text}")

        if share_with:
            try:
                _share_with(ts, [r for r in all_responses if not r.is_error], share_with)
            except HTTPStatusError as e:
                log.error(f"Unable to share: {e.response.text}")

    # display the mapping file details.
    if show_mapping:
        show_mapping_details(ts=ts, path=tmlfs.path, source=source, dest=dest, org=org)

    print('done')


def _check_parameters(
        path: pathlib.Path,  # root of the TML file system.
        guid: GUID,  # GUID for the TML to import if only one is being imported.
        source: str,  # Source of the TML being imported.  Used for mapping.
        dest: str,  # Destination of the TML being imported.  Used for mapping.
        include_types: Optional[List[str]],  # Types of TML to import.
        exclude_types: Optional[List[str]],  # Types of TML to exclude from import.
):
    """
    Checks the parameters to make sure they make sense together.  If not, then raise an exception.
    """
    if (source or dest) and not (source and dest):
        error_msg = "source specified, but not destination" if source else "destination specified, but not source"
        raise CSToolsError(error=error_msg, reason="Source and destination must both be specified.",
                           mitigation="Specify both source and destination when using mapping.")

    path_mitigation = "The path must exist and be a valid TML file system."
    if not path.exists():
        raise CSToolsError(error=f"Path {path} does not exist.", mitigation=path_mitigation)

    if not (path / ".tmlfs"):
        raise CSToolsError(error=f"Path {path} does not appear to be a TML file system.", mitigation=path_mitigation)

    if guid and (include_types or exclude_types):
        raise CSToolsError(error="A guid and include/exclude specified.",
                           reason="Cannot specify both a file and include/exclude types.",
                           mitigation="Specify either a file or include/exclude types, but not both.")


def _load_from_file(
        ts: ThoughtSpot,
        tmlfs: ImportTMLFS,
        guid: GUID,
        import_policy: TMLImportPolicy,
        force_create: bool,
        mapping_file: GUIDMapping,
) -> List[TMLImportResponse]:
    all_responses: List[TMLImportResponse] = []

    tml = tmlfs.load_tml_for_guid(guid)

    if tml.tml_type_name == TMLType.connection:
        responses = _load_connections(ts, tmlfs, [tml], import_policy, force_create, mapping_file)
        all_responses.extend(responses)
    else:
        responses = _load_tml(ts, tmlfs, [tml], import_policy, force_create, mapping_file)
        all_responses.extend(responses)

    return all_responses


def _load_from_dir(
        ts: ThoughtSpot,
        tmlfs: ImportTMLFS,
        import_policy: TMLImportPolicy,
        force_create: bool,
        mapping_file: GUIDMapping,
        include_types: Optional[List[str]],
        exclude_types: Optional[List[str]],
) -> List[TMLImportResponse]:
    all_responses: List[TMLImportResponse] = []

    # Determine the types of TML to import.
    types_to_import = include_types or [_ for _ in TMLType]
    if exclude_types:
        types_to_import = [TMLType(_) for _ in types_to_import if _ not in exclude_types]

    # First load the connections.  Those need to be done first and use different APIs.
    if types_to_import and TMLType.connection in types_to_import:
        connection_tml = tmlfs.load_tml([TMLType.connection])
        responses = _load_connections(ts, tmlfs, connection_tml, import_policy, force_create, mapping_file)
        all_responses.extend(responses)

    # Now load all types remaining that were requested.
    other_types = [_ for _ in TMLType if _ != TMLType.connection and _ in types_to_import]
    if other_types:
        other_tml = tmlfs.load_tml(other_types)
        responses = _load_tml(ts, tmlfs, other_tml, import_policy, force_create, mapping_file)
        all_responses.extend(responses)

    return all_responses


def _load_connections(
        ts: ThoughtSpot,
        tmlfs: ImportTMLFS,
        connection_tml: [TML],
        import_policy: TMLImportPolicy,
        force_create: bool,
        mapping_file: GUIDMapping,
) -> List[TMLImportResponse]:
    responses: List[TMLImportResponse] = []

    old_guids = []
    for tml in connection_tml:
        old_guid = tml.guid if tml.guid else None
        old_guids.append(old_guid)
        mapping_file.disambiguate(tml=tml, delete_unmapped_guids=force_create)
        tmlfs.log_tml(tml=tml, old_guid=old_guid)

    if import_policy == TMLImportPolicy.validate:
        log.warning("Warning: connections don't support validate only policies.  Ignoring connections.")
        return responses  # connection APIs don't support validate_only.

    if import_policy == TMLImportPolicy.all_or_none:
        log.warning(
            f"Warning: connections don't support 'ALL_OR_NONE' policies.  "
            f"Using {TMLImportPolicy.partial} for connections."
        )

    # make sure there are passwords.  If not, then the connection will create, but tables will fail.
    _verify_connection_passwords(connection_tml)

    if force_create:
        responses = _create_connections(ts, tmlfs, connection_tml=connection_tml)
    else:
        responses = _update_connections(ts, tmlfs, connection_tml=connection_tml)

    # If some TML failed, then the GUIDs shouldn't be added to the map.
    new_old_guids, new_guids = _get_guids_to_map(old_guids=old_guids, responses=responses)
    mapping_file.set_mapped_guids(new_old_guids, new_guids)  # might be the same, but that's OK.

    _wait_for_metadata(ts=ts, guids=new_guids)

    return responses


def _verify_connection_passwords(connection_tml: [TML]) -> None:
    """
    Verify that all connections have passwords.  If not, raise an exception.
    :param connection_tml: The list of connection TML.
    """
    for tml in connection_tml:

        # connections without passwords can be created, but then the following table create fails (and you
        # get errors in the UI.  So throw an exception to avoid future pain.
        for p in tml.connection.properties:
            if p.key == "password" and p.value:
                break
        else:
            raise CSToolsError(
                error=f'Connection "{tml.connection.name}" missing password',
                reason="Connections require a valid password to create tables.",
                mitigation="Add a password to the connection file and try again.",
            )


def _create_connections(
        ts: ThoughtSpot,
        tmlfs: ImportTMLFS,
        connection_tml: [TML],
) -> List[TMLImportResponse]:
    """
    Creates a new connection.  Note that tables are not created as part of the conneciton and must be created
    separately.  This will create an empty connection.
    :param ts: The ThoughtSpot instance.
    :param tmlfs: The ThoughtSpot TML file system.
    :param connection_tml: The TML to create.
    """

    responses: List[TMLImportResponse] = []

    for tml in connection_tml:

        log.info(f"Creating connection {tml.connection.name} ({tml.guid})")
        tmlfs.log_tml(tml)

        try:
            r = ts.api.connection_create(
                name=tml.name,
                description="",
                external_database_type=tml.connection.type,
                create_empty=True,
                metadata=tml.to_rest_api_v1_metadata(),
            )

            # Add the results to the response list.
            if not r.is_success:  # failed

                responses.append(
                    TMLImportResponse(
                        guid=tml.guid,
                        metadata_object_type="DATA_SOURCE",
                        tml_type_name="connection",
                        name=tml.name,
                        status_code=r.reason_phrase,
                        error_messages=[str(r.status_code)]
                    )
                )

            else:  # succeeded

                d = r.json()
                data = d.get("dataSource", d)

                responses.append(
                    TMLImportResponse(
                        guid=data["header"]["id"],
                        metadata_object_type="DATA_SOURCE",
                        tml_type_name="connection",
                        name=data["header"]["name"],
                        status_code=r.reason_phrase if r.reason_phrase else "OK",
                        error_messages=[],
                    )
                )

        except HTTPStatusError as e:
            rich_console.log(f"Error creating connection {tml.name}: {e}.")
            rich_console.log("\tVerify connection file and connection user.")
            # needed to get a GUID to map for mapping.
            responses.append(
                TMLImportResponse(
                    guid=tml.guid,  # Not sure if this will cause problems since it will map back to itself.
                    metadata_object_type="DATA_SOURCE",
                    tml_type_name="connection",
                    name=tml.name,
                    status_code="ERROR",
                    error_messages=[e.response.content.decode("utf-8")]
                )
            )

    return responses


def _update_connections(ts: ThoughtSpot,
                        tmlfs: ImportTMLFS,
                        connection_tml: [TML],
                        ) -> List[TMLImportResponse]:
    """
    Updates an existing connection.  Checks to see if the connection actually exists and will create if not.
    Note that when creating a connection the tables aren't created.  But when updating, the tables are updated.
    This is an artifact of how the connection APIs work.  Future releases are supposed to decouple connections
    and tables.
    :param ts: The ThoughtSpot instance.
    :param tmlfs: The ThoughtSpot TML file system.
    :param connection_tml: The TML for the connection to update.
    """
    responses: List[TMLImportResponse] = []

    # connections are processed one at a time.
    for tml in connection_tml:

        # if it doesn't exist, we have to call and create it.
        existing_connection = _get_connection(ts, tml.guid)
        if not existing_connection:
            create_responses = _create_connections(ts, tmlfs, [tml])
            responses.extend(create_responses)

        else:
            # if it does exist, we have to update it.  Note that tables are only allowed to be created via TML (per
            # scriptability rules, not API) to be consistent with create.
            _remove_new_tables_from_connection(tml, existing_connection)

            log.info(f"Updating connection {tml.connection.name} ({tml.guid})")
            tmlfs.log_tml(tml)

            try:
                r = ts.api.connection_update(
                    guid=tml.guid,
                    name=tml.name,
                    description="",
                    external_database_type=tml.connection.type,
                    metadata=tml.to_rest_api_v1_metadata(),
                )

                if not r.is_success:
                    status_code = r.reason_phrase
                    error_messages = str(r.status_code)
                    name = tml.name
                    log.error(f"Error updating connection {name} ({tml.guid}): {error_messages}")

                    responses.append(
                        TMLImportResponse(
                            guid=tml.guid,
                            metadata_object_type="DATA_SOURCE",
                            tml_type_name="connection",
                            name=tml.name,
                            status_code=status_code,
                            error_messages=[error_messages],
                        )
                    )

                else:
                    d = r.json()
                    data = d.get("dataSource", d)

                    responses.append(
                        TMLImportResponse(
                            guid=data["header"]["id"],
                            metadata_object_type="DATA_SOURCE",
                            tml_type_name="connection",
                            name=data["header"]["name"],
                            status_code="ERROR" if r.reason_phrase else "OK",
                            error_messages=[r.reason_phrase],
                        )
                    )

            except HTTPStatusError as e:
                rich_console.log(f"Error updating connection {tml.name}: {e} {e.response.content.decode('utf-8')}")
                # needed to get a GUID to map for mapping.
                responses.append(
                    TMLImportResponse(
                        guid=tml.guid,  # Not sure if this will cause problems since it will map back to itself.
                        metadata_object_type="DATA_SOURCE",
                        tml_type_name="connection",
                        name=tml.name,
                        status_code="ERROR",
                        error_messages=[e.args[0], e.response.content.decode("utf-8")]
                    )
                )

    return responses


def _get_connection(ts: ThoughtSpot, connection_guid: GUID) -> Optional[Connection, None]:
    """
    Returns true if the connection with the given GUID exists.
    :param ts: The ThoughtSpot instance.
    :param connection_guid: The GUID for the connection to check.
    :return:  True if the connection exists.
    """
    try:
        r = ts.api.connection_export(guid=connection_guid)
        cnx = Connection.loads(r.text)
        cnx.guid = connection_guid
        return cnx
    except HTTPStatusError as e:
        if e.response.status_code == 404:  # the API will return a 400 if the connection doesn't exist.
            return None
        else:
            raise CSToolsError(error=f"Unknown error checking for connection {connection_guid}: {e}",
                               reason=str(e.response.content),
                               mitigation="Verify TS connection and GUID")
    except TMLDecodeError as e:
        raise CSToolsError(error=f"Error decoding connection {connection_guid}: {e}",
                           mitigation="Verify TS connection and GUID")


def _remove_new_tables_from_connection(new_connection: Connection, existing_connection: Connection) -> None:
    """
    This is only relevant for updates of connections.  We are limiting creation of tables to table TML, so we need to
    remove any new tables from the new connection.
    :param new_connection: The new connection that might have new tables.  The tables will be removed.
    :param existing_connection: The existing connection to use for comparison.

    Note: This could be made more efficient, but there will likely be a small number of tables, so it's not worth it.
    """

    # The tables are list of tables inside the connection.  They can be different sizes.  Remove from the
    # new connection any tables that aren't in the existing connection.
    tables_to_remove = []
    nbr_new_tables = len(new_connection.connection.table) if new_connection.connection.table else 0
    nbr_existing_tables = len(existing_connection.connection.table) if existing_connection.connection.table else 0
    for cnt in range(max(nbr_new_tables, nbr_existing_tables)):
        if cnt >= nbr_new_tables:
            break
        table = new_connection.connection.table[cnt]

        found = False
        if nbr_existing_tables:  # only do if there are tables.
            for (idx, existing_table) in enumerate(existing_connection.connection.table):
                if table.external_table.db_name == existing_table.external_table.db_name \
                        and table.external_table.schema_name == existing_table.external_table.schema_name \
                        and table.external_table.table_name == existing_table.external_table.table_name:
                    found = True
                    break

        if not found:  # this is a new table.
            log.info(f"Removing new table {table.name} from connection {new_connection.name}")
            tables_to_remove.append(table)

    for table in tables_to_remove:
        new_connection.connection.table.remove(table)


def _load_tml(ts, tmlfs: ImportTMLFS, tml_list: [TML], import_policy: TMLImportPolicy, force_create: bool, mapping_file
              ) -> List[TMLImportResponse]:
    responses: List[TMLImportResponse] = []

    if not tml_list:
        return responses

    old_guids = []

    for tml in tml_list:
        log.info(f"Importing {tml.name} ({tml.guid})")

        # remember the original GUIDs since they can change with the mapping.
        old_guid = tml.guid
        old_guids.append(old_guid)

        # if we are forcing the creation of new content, we want to delete guids that aren't mapped
        mapping_file.disambiguate(tml=tml, delete_unmapped_guids=force_create)
        tml = _remove_viz_guid(tml)
        tmlfs.log_tml(tml, old_guid)  # write the updated TML to the logs

    r = ts.api.metadata_tml_import(
        import_objects=[tml.dumps() for tml in tml_list],
        import_policy=import_policy,
        force_create=force_create,
    )

    guids_to_map: Dict[GUID, GUID] = {}

    guid_cnt = 0
    for obj in r.json()["object"]:
        old_guid = old_guids[guid_cnt]

        status_code = obj["response"]["status"]["status_code"]

        if status_code == "ERROR":
            guid = old_guid
            name = tml_list[guid_cnt].name
            metadata_type = TMLSupportedContent.from_friendly_type(tml_list[guid_cnt].tml_type_name)
            # subtype = TMLSupportedContentSubtype.from_friendly_type(tml_list[guid_cnt].tml_type_name)
        else:  # not an error
            guid = obj["response"].get("header", {}).get("id_guid")
            name = obj["response"].get("header", {}).get("name")
            # subtype = obj["response"].get("header", {}).get("type", "")
            metadata_type = obj["response"].get("header", {}).get("metadata_type")

        if obj["response"]["status"]["status_code"] != "ERROR":
            guids_to_map[old_guid] = guid

        status_code = obj["response"]["status"]["status_code"]
        error_messages = obj["response"]["status"].get("error_message", None)
        log.info(f"Imported {metadata_type} {name} ({guid}) with status {status_code} and message {error_messages}")

        responses.append(
            TMLImportResponse(
                guid=guid,
                metadata_object_type=metadata_type,
                tml_type_name=tml_list[guid_cnt].tml_type_name,
                name=name,
                status_code=status_code,
                error_messages=error_messages
            )
        )

        guid_cnt += 1


    # Have to make sure it's not an error.  is_success is False on warnings, but content is created.
    is_error_free = all(not r.is_error for r in responses)

    if import_policy != TMLImportPolicy.validate:  # no need to update or wait if only validating.

        if is_error_free or import_policy != TMLImportPolicy.all_or_none:
            for old_guid, new_guid in guids_to_map.items():
                mapping_file.set_mapped_guid(old_guid, new_guid)
                mapping_file.save()

            _wait_for_metadata(ts=ts, guids=[imported_object.guid for imported_object in responses])

    return responses


def _get_guids_to_map(old_guids: List[GUID], responses: List[TMLImportResponse]) -> Tuple[List[GUID], List[GUID]]:
    """
    Returns a list of old guid to new guid mapping.  Responses that had errors are ignored because they didn't map.
    :param old_guids: The old GUIDs for the imported content.
    :param responses: The responses from the call.
    :return: The old GUIDs and the new GUIDs to use for mapping.
    """
    idx = 0
    new_old_guids = []
    new_guids = []
    for r in responses:
        # don't map if there is an error or if there was no original GUID.
        if not r.is_error and old_guids[idx]:
            new_old_guids.append(old_guids[idx])
            new_guids.append(r.guid)
        idx += 1

    return new_old_guids, new_guids


def _wait_for_metadata(ts: ThoughtSpot, guids: List[GUID]) -> None:
    """
    Waits on the existence of metadata objects.  There can be a delay between creation and being available.
    """
    ready_guids = set()
    n = 0

    # when all content is ready, this returns an empty set
    while set(guids).difference(ready_guids):
        n += 1
        log.info(f"checking {len(guids): >3} guids, n={n}")

        for metadata_type in ("DATA_SOURCE", "LOGICAL_TABLE", "QUESTION_ANSWER_BOOK", "PINBOARD_ANSWER_BOOK"):
            for chunk in chunks(list(set(guids).difference(ready_guids)), n=25):
                r = ts.api.metadata_list(metadata_type=metadata_type, fetch_guids=list(chunk), show_hidden=False)

                for metadata_object in r.json()["headers"]:
                    ready_guids.add(metadata_object["id"])

        time.sleep(5.0)


def _some_tml_updated(import_policy: TMLImportPolicy, results: List[TMLImportResponse]) -> bool:
    """
    Returns True if any of the TML was updated.  This is known based on the policy and results:
    * Validate - always False
    * All or none - True if/ all the items don't have errors.
    * Partial - True if any of the items don't have errors.
    """
    if import_policy == TMLImportPolicy.validate:  # if validating, then no content would be created.
        return False

    if import_policy == TMLImportPolicy.all_or_none:
        return all([not r.is_error for r in results])  # if any of the results weren't an error, return true.

    if import_policy == TMLImportPolicy.partial:
        return any([not r.is_error for r in results])  # if any of the results weren't an error, return true.

    return False  # this should never happen, but just in case a new value is added.


def _show_results_as_table(results: List[TMLImportResponse]) -> None:
    """
    Writes a pretty results table to the rich_console.
    """
    table = Table(title="Import Results", width=300)

    table.add_column("Status", justify="center", width=10)  # 4 + length of literal: status
    table.add_column("GUID", width=20)  # 4 + length of guid (36)  - was 40, but making shorter for longer error.
    # table.add_column("Type", justify="center", width=13)  # 4 + length of "worksheet"
    table.add_column("Name", justify="center", width=16)  # Will wrap the name.
    table.add_column("Error", width=150 - 10 - 20 - 16)  # 150 max minus previous.

    for r in results:
        try:
            error_messages = ' '.join(r.error_messages) if r.error_messages else ""
            table.add_row(r.status_code, r.guid, r.name, error_messages)
        except Exception as e:
            rich_console(f"Error adding row for {r.name}: {e}")

    rich_console.print(Align.center(table))


def _add_tags(ts: ThoughtSpot, objects: List[TMLImportResponse], tags: List[str]) -> None:
    """
    Adds the tags to the items in the response.
    :param ts: The ThoughtSpot object.
    :param objects: List of the objects to add the tags to.
    :param tags: List of tags to create.
    """
    with rich_console.status(f"[bold green]adding tags: {tags}[/]"):
        ids = []
        types = []
        for _ in objects:
            ids.append(_.guid)
            types.append(_.metadata_object_type)
        if ids:  # might all be errors
            log.info(f"Adding tags {tags} to {ids}")
            try:
                ts.api.metadata_assign_tag(metadata_guids=ids, metadata_types=types, tag_names=tags)
            except HTTPStatusError as e:
                log.error(f"Error adding tags {tags} for metadata {ids}: {types}. Error: {e}")


def _share_with(ts: ThoughtSpot, objects: List[TMLImportResponse], share_with: List[str]) -> None:
    """
    Shares the objects with the groups.
    :param ts: The ThoughtSpot interface object.
    :param objects: Objects to share with.
    :param share_with: The list of group names to share with.
    :return:
    """
    with rich_console.status(f"[bold green]sharing with: {share_with}[/]"):
        groups = []
        for group in share_with:
            try:
                groups.append(ts.group.guid_for(group))
            except HTTPStatusError as e:
                log.error(f"unable to get ID for group {group}: {e}")

        if groups:  # make sure some mapped

            # Bundling by type to save on calls.
            type_bundles = {}
            for _ in objects:
                # Connection sharing is available in 9.3+
                if _.metadata_object_type == MetadataObjectType.connection and \
                        ts.platform.version < AwesomeVersion("9.3.0"):
                    continue

                guid_list = type_bundles.get(_.metadata_object_type, [])
                if not guid_list:
                    type_bundles[_.metadata_object_type] = guid_list
                guid_list.append(_.guid)

            permissions = {}
            for g in groups:
                permissions[g] = ShareModeAccessLevel.can_view

            for ctype in type_bundles.keys():
                objectids = type_bundles[ctype]
                try:
                    # for some bizarre reason you can only share connections one at a time.
                    if ctype == MetadataObjectType.connection:
                        for objectid in objectids:
                            ts.api.security_share(metadata_type=ctype, guids=[objectid], permissions=permissions)
                    else:
                        ts.api.security_share(metadata_type=ctype, guids=objectids, permissions=permissions)
                except HTTPStatusError as e:
                    log.error(f"Unable to share {objectids} of type {ctype} with permissions: {permissions}: {e}")


def _remove_viz_guid(tml):
    attrs = _recursive_scan(tml, check=lambda attr: hasattr(attr, "viz_guid"))

    for liveboard_visualization in attrs:
        liveboard_visualization.viz_guid = None

    return tml
