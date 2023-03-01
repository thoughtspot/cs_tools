"""
This file contains the methods to execute the 'scriptability import' command.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict
import pathlib
import logging
import time
import copy
import re
import traceback

from thoughtspot_tml.utils import _recursive_scan
from thoughtspot_tml.utils import determine_tml_type
from rich.align import Align
from rich.table import Table
from httpx import HTTPStatusError

from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.errors import CSToolsError
from cs_tools.cli.ux import rich_console
from cs_tools.types import ShareModeAccessLevel, TMLSupportedContent, MetadataObjectType, TMLImportPolicy, GUID
from cs_tools.api import _utils

from .util import GUIDMapping, TMLFile

log = logging.getLogger(__name__)


@dataclass
class TMLImportResponse:
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

    @property
    def is_error(self) -> bool:
        return self.status_code == "ERROR"


def to_import(
    ts,
    path,
    import_policy,
    force_create,
    guid_file,
    from_env,
    to_env,
    tags,
    share_with,
    tml_logs,
    org,
):
    """
    Import TML from a file or directory into ThoughtSpot.

    \b
    cs_tools dependends on thoughtspot_tml. The GUID file is produced from
    thoughtspot_tml and requires a specific format. For further information on the
    GUID File, see

       https://github.com/thoughtspot/thoughtspot_tml/tree/v2_0_release#environmentguidmapper
    """
    if guid_file is not None and not (from_env and to_env):
        raise CSToolsError(
            error="GUID files also require specifying the '--from-env' and '--to-env' options.",
            reason="Insufficient information to perform GUID mapping.",
            mitigation="Set the --from-env and --to-env values.",
        )

    if org is not None:
        ts.org.switch(org)

    guid_mapping = GUIDMapping(from_env=from_env, to_env=to_env, path=guid_file) if guid_file is not None else None

    if import_policy == TMLImportPolicy.validate:
        log.info(f"validating from {path}")
        results = _import_and_validate(ts, path, force_create, guid_mapping, tml_logs)

    else:
        log.info(f"importing from {path} with policy {import_policy}")
        results = _import_and_create_bundle(ts, path, import_policy, force_create, guid_mapping, tags,
                                            share_with, tml_logs)

    _show_results_as_table(results)


def _import_and_validate(
    ts: ThoughtSpot, path: pathlib.Path, force_create: bool, guid_mapping: GUIDMapping, tml_logs: pathlib.Path
) -> List[TMLImportResponse]:
    """
    Perform a validation import.

    No content is created. If FQNs map, they will be used. If they don't, they will be removed.
    """
    tml_files: List[TMLFile] = []

    for guid, tml_file in _load_tml_from_files(path).items():
        if tml_file.is_connection:
            log.warning(f"connection validation is not supported. ignoring {tml_file.filepath.name}")
            continue

        # There may be an issue with the delete_unmapped logic.  If new content is being validated that has FQNs that
        # aren't in the target system, then those would need to be deleted. But if it's validating against existing
        # content then it wouldn't.
        if guid_mapping is not None:
            guid_mapping.disambiguate(tml_file.tml, delete_unmapped_guids=True)
            tml_file.tml = _remove_viz_guid(tml_file.tml)

        # strip GUIDs if doing force create and convert to a list of TML string.
        if force_create:
            tml_file.tml.guid = None

        if tml_logs is not None:
            filename = tml_file.filepath.name.split(".")[0]
            content_type = tml_file.tml.tml_type_name
            tml_file.tml.dump(tml_logs / f"{filename}.IMPORTED.{content_type}.tml")

        log.info(f"validating {tml_file.filepath.name}")
        tml_files.append(tml_file)

    with rich_console.status(f"[bold green]importing {path.name}[/]"):
        r = ts.api.metadata_tml_import(
            import_objects=[tml_file.tml.dumps() for tml_file in tml_files],
            import_policy=TMLImportPolicy.validate,
            force_create=force_create,
        )

        results: List[TMLImportResponse] = []

        for tml_file, content in zip(tml_files, r.json()["object"]):
            status_code = content["response"]["status"]["status_code"]
            error_messages = content["response"]["status"].get("error_message", None)
            name = tml_file.filepath.stem

            _log_results_error(name=name, status_code=status_code, error_messages=error_messages)


            results.append(
                TMLImportResponse(
                    guid=content["response"].get("header", {}).get("id_guid", tml_file.tml.guid),
                    metadata_object_type=TMLSupportedContent[tml_file.tml.tml_type_name].value,
                    tml_type_name=tml_file.tml.tml_type_name,
                    name=name,
                    status_code=status_code,
                    error_messages=error_messages,
                )
            )

    return results


def _import_and_create_bundle(
    ts: ThoughtSpot,
    path: pathlib.Path,
    import_policy: TMLImportPolicy,
    force_create: bool,
    guid_mapping: GUIDMapping,
    tags: List[str],
    share_with: List[str],
    tml_logs: pathlib.Path,
) -> List[TMLImportResponse]:
    """
    Attempts to create new content. If a mapping is not found, then an assumption is made that the mapping is correct.
    """
    tml_files: List[TMLFile] = []
    cnxn_files: List[TMLFile] = []

    for guid, tml_file in _load_tml_from_files(path).items():
        cnxn_files.append(tml_file) if tml_file.is_connection else tml_files.append(tml_file)

        # strip GUIDs if doing force create and convert to a list of TML string.
        if force_create:
            tml_file.tml.guid = None

    results = []

    try:
        with rich_console.status(f"[bold green]importing {path.name}[/]"):
            # === IMPORT ORDER ===
            # 1. CONNECTIONS
            # 2. TML
            kw = {
                "ts": ts,
                "guid_mapping": guid_mapping,
                "tml_logs": tml_logs,
                "import_policy": import_policy,
                "force_create": force_create,
            }

            if cnxn_files:
                r, connection_tables = _upload_connections(**kw, connection_file_bundles=cnxn_files)
                results.extend(r)
            else:
                # connection name --> table names
                connection_tables: Dict[str, str] = {}

            if tml_files:
                r = _upload_tml(**kw, tml_file_bundles=tml_files, connection_tables=connection_tables)
                results.extend(r)

    # log the error, but let any content that got imported still get tagged and shared
    except Exception as e:
        traceback.print_exc()
        log.error(f"error loading content: {e}, see logs for details.")
        log.debug(e, exc_info=True)

    if guid_mapping:
        guid_mapping.save()

    if _some_tml_updated(import_policy, results):  # only update and share if there were actual updates.
        if tags:
            _add_tags(ts, [r for r in results if not r.is_error], tags)

        if share_with:
            _share_with(ts, [r for r in results if not r.is_error], share_with)

    return results


def _load_tml_from_files(path: pathlib.Path) -> Dict[GUID, TMLFile]:
    """
    Loads the TML files, returning a list of file names and the TML mapping from GUID to TML object.
    :param path: The path to the TML files (either a file or directory)
    :return: A dictionary of GUIDs to TML file bundles (path and TML object). Only files to be loaded will be included.
    """
    tml_file_bundles: Dict[GUID, TMLFile] = {}

    if path.is_file():
        filepaths = [path]
    else:
        filepaths = [p for p in path.iterdir() if p.as_posix().endswith((".tml", ".yaml", ".yml"))]

    for path in filepaths:
        tml_cls = determine_tml_type(path=path)
        tml = tml_cls.load(path)
        name, dot, extra = path.name.partition(".")

        if tml.guid is None and _utils.is_valid_guid(name):
            tml.guid = name

        tml_file_bundles[tml.guid] = TMLFile(filepath=path, tml=tml)

    log_bundle = ", ".join([tml_file.filepath.name for tml_file in tml_file_bundles.values()])
    log.info(f"Attempting to load: {log_bundle}")

    return tml_file_bundles


def _upload_connections(
    ts: ThoughtSpot,
    guid_mapping: GUIDMapping,
    connection_file_bundles: List[TMLFile],
    tml_logs: pathlib.Path,
    import_policy: TMLImportPolicy,
    force_create: bool,
) -> tuple[List[TMLImportResponse], Dict[str, List[str]]]:
    """
    Uploads connections.
    """
    responses: List[TMLImportResponse] = []
    connection_tables: Dict[str, List[str]] = {}  # connection name --> table names

    if import_policy == TMLImportPolicy.validate:
        log.warning("Warning: connections don't support validate only policies.  Ignoring connections.")
        return responses, connection_tables  # connection APIs don't support validate_only.

    if import_policy == TMLImportPolicy.all_or_none:
        log.warning(
            f"Warning: connections don't support 'ALL_OR_NONE' policies.  "
            f"Using {TMLImportPolicy.partial} for connections."
        )

    for tml_file in connection_file_bundles:
        tml = tml_file.tml

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

        if tml_logs is not None:
            filename = tml_file.filepath.name.split(".")[0]
            content_type = tml_file.tml.tml_type_name
            tml_file.tml.dump(tml_logs / f"{filename}.IMPORTED.{content_type}.tml")

        if force_create:
            # If creating, and have tables in the connection and then create, you end up with the tables
            # being created twice and the second time fails.  Delete the tables from the connection in these
            # scenarios, so they get created from TML.  Not sure if older versions support this capability.
            # This also requires the TML for tables be exported.
            # HOWEVER, for connection updates, you have to have the tables.  This may be a bug.

            r = ts.api.connection_create(
                name=tml.name,
                description="",
                external_database_type=tml.connection.type,
                create_empty=True,
                metadata=tml.to_rest_api_v1_metadata(),
            )

        else:
            r = ts.api.connection_update(
                guid=guid_mapping.get_mapped_guid(tml.guid),
                name=tml.name,
                description="",
                external_database_type=tml.connection.type,
                metadata=tml.to_rest_api_v1_metadata(),
            )

        if not r.is_success:
            status_code = r.reason_phrase
            error_messages = str(r.status_code)
            name = tml.name
            _log_results_error(name=name, status_code=status_code, error_messages=error_messages)

            responses.append(
                TMLImportResponse(
                    guid=tml.guid,
                    metadata_object_type="DATA_SOURCE",
                    tml_type_name="connection",
                    name=tml.name,
                    status_code=status_code,
                    error_messages=error_messages,
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
                    status_code=r.reason_phrase if r.reason_phrase else "OK",
                    error_messages=str(r.status_code),
                )
            )

            # PROCESS IMPORTED TABLES
            connection_tables[tml.connection.name] = []

            for table in data["logicalTableList"]:
                r = TMLImportResponse(
                    guid=table["header"]["id"],
                    metadata_object_type="LOGICAL_TABLE",
                    tml_type_name="table",
                    name=table["header"]["name"],
                    status_code="OK",
                    error_messages=None,
                )
                connection_tables[tml.connection.name].append(r)
                responses.append(r)

            # WRITE GUID MAPPINGS TO FILE
            if guid_mapping is not None:
                # If the guid was deleted (usually because of force-create, then get it from the file name.
                guid = tml.guid if tml.guid else tml_file.filepath.name.split('.')[0]
                guid_mapping.set_mapped_guid(guid, data["header"]["id"])

                old_table_guids = {t.name: t.id for t in tml.connection.table} if tml.connection.table else {}

                for table in data["logicalTableList"]:
                    old_guid = old_table_guids.get(table["header"]["name"])
                    new_guid = table["header"]["id"]
                    guid_mapping.set_mapped_guid(old_guid, new_guid)

    # CONNECTIONS ARE ALWAYS PARTIAL, WAIT FOR THE CREATED ONES
    _wait_for_metadata(ts=ts, guids=[imported_object.guid for imported_object in responses])

    return responses, connection_tables


def _upload_tml(
    ts: ThoughtSpot,
    guid_mapping: GUIDMapping,
    tml_file_bundles: List[TMLFile],
    tml_logs: pathlib.Path,
    import_policy: TMLImportPolicy,
    force_create: bool,
    connection_tables: Dict[str, List[str]],
) -> List[TMLImportResponse]:

    responses: List[TMLImportResponse] = []

    if not connection_tables:
        updated = copy.copy(tml_file_bundles)
    else:
        # if there were connections, then we need to exclude tables that were part of the connection.
        updated = []

        for tml_file in tml_file_bundles:
            if isinstance(tml_file.tml, Table):
                connection = tml_file.tml.table.connection.name
                table = tml_file.tml.table.name

                if not (connection in connection_tables and table in connection_tables[connection]):
                    updated.append(tml_file)

            else:
                updated.append(tml_file)

    # No remaining TML, so just return with empty results.
    if not updated:
        return responses

    for tml_file in updated:

        # if we are forcing the creation of new content, we want to delete guids that aren't mapped
        if guid_mapping:
            guid_mapping.disambiguate(tml=tml_file.tml, delete_unmapped_guids=force_create)
            tml_file.tml = _remove_viz_guid(tml_file.tml)

        if tml_logs is not None:
            filename = tml_file.filepath.name.split(".")[0]
            content_type = tml_file.tml.tml_type_name
            tml_file.tml.dump(tml_logs / f"{filename}.IMPORTED.{content_type}.tml")

    r = ts.api.metadata_tml_import(
        import_objects=[tml_file.tml.dumps() for tml_file in updated],
        import_policy=import_policy,
        force_create=force_create,
    )

    guids_to_map: Dict[GUID, GUID] = {}

    for tml_file, content in zip(updated, r.json()["object"]):
        old_guid = tml_file.tml.guid if tml_file.tml.guid else tml_file.filepath.name.split('.')[0]
        guid = content["response"].get("header", {}).get("id_guid", tml_file.tml.guid)
        type = content["response"].get("header", {}).get("type", tml_file.tml.tml_type_name)
        name = content["response"].get("header", {}).get("name", tml_file.filepath.stem)

        if content["response"]["status"]["status_code"] != "ERROR":
            guids_to_map[old_guid] = guid

        status_code = content["response"]["status"]["status_code"]
        error_messages = content["response"]["status"].get("error_message", None)
        name = tml_file.filepath.stem
        _log_results_error(name=name, status_code=status_code, error_messages=error_messages)

        responses.append(
            TMLImportResponse(
                guid=guid,
                metadata_object_type=TMLSupportedContent[tml_file.tml.tml_type_name].value,
                tml_type_name=type,
                name=name,
                status_code=content["response"]["status"]["status_code"],
                error_messages=content["response"]["status"].get("error_message", None),
            )
        )

    # Have to make sure it's not an error.  is_success is False on warnings, but content is created.
    is_error_free = all(not r.is_error for r in responses)

    if is_error_free or import_policy != TMLImportPolicy.all_or_none:
        if guid_mapping is not None:
            for old_guid, new_guid in guids_to_map.items():
                guid_mapping.set_mapped_guid(old_guid, new_guid)
            guid_mapping.save()

        _wait_for_metadata(ts=ts, guids=[imported_object.guid for imported_object in responses])

    return responses


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
            except Exception as e:
                log.error(f"Error adding tags: {e}\nCheck spelling of the tag.")


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
                # connections don't support sharing as-of 8.9
                # TODO consider if this should be allowed for 9.0+.  Possible, but maybe not desired.
                if _.metadata_object_type == MetadataObjectType.connection:
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
                    ts.api.security_share(metadata_type=ctype, guids=objectids, permissions=permissions)
                except HTTPStatusError:
                    log.error(f"Unable to share {objectids} of type {ctype} with permissions: {permissions}")


def _wait_for_metadata(ts: ThoughtSpot, guids: List[GUID]) -> None:
    ready_guids = set()
    n = 0

    # when all content is ready, this returns an empty set
    while set(guids).difference(ready_guids):
        n += 1
        log.info(f"checking {len(guids): >3} guids, n={n}")

        r_c = ts.api.metadata_list(metadata_type="DATA_SOURCE", fetch_guids=list(guids), show_hidden=False)
        r_t = ts.api.metadata_list(metadata_type="LOGICAL_TABLE", fetch_guids=list(guids), show_hidden=False)
        r_a = ts.api.metadata_list(metadata_type="QUESTION_ANSWER_BOOK", fetch_guids=list(guids), show_hidden=False)
        r_p = ts.api.metadata_list(metadata_type="PINBOARD_ANSWER_BOOK", fetch_guids=list(guids), show_hidden=False)

        for response in (r_c, r_t, r_a, r_p):
            for header in response.json()["headers"]:
                ready_guids.add(header["id"])

        time.sleep(5.0)


def _show_results_as_table(results: List[TMLImportResponse]) -> None:
    """
    Writes a pretty results table to the rich_console.
    """
    table = Table(title="Import Results", width=150)

    table.add_column("Status", justify="center", width=10)   # 4 + length of literal: status
    # table.add_column("Filename", width=48)                 # 4 + length of "guid.type.tml"
    table.add_column("GUID", width=36)                       # 4 + length of "guid.type.tml"
    table.add_column("Type", justify="center", width=13)     # 4 + length of "worksheet"
    table.add_column("Error", no_wrap=True, width=150 - 10 - 13 - 48)  # 150 max minus previous.

    for r in results:
        # table.add_row(r.status_code, r.tml_type_name, r.name, ','.join(r.error_messages))
        # table.add_row(r.status_code, r.guid, r.tml_type_name, ','.join(r.error_messages))
        table.add_row(r.status_code, r.name, r.tml_type_name, ','.join(r.error_messages))

    rich_console.print(Align.center(table))


def _log_results_error (name: str, status_code: str, error_messages: str) -> None:
    """
    Logs a message if there was a WARNING or ERROR.
    """
    msg = f"{name} -- ${error_messages}"

    if status_code == "WARNING":
        log.warning(msg=msg)
    elif status_code == "ERROR":
        log.error(msg=msg)


def _some_tml_updated(import_policy: TMLImportPolicy, results: List[TMLImportResponse]) -> bool:
    """
    Returns True if any of the TML was updated.  This is known based on the policy and results:
    * Validate - always False
    * All or none - True if all the items don't have errors.
    * Partial - True if any of the items don't have errors.
    """
    if import_policy == TMLImportPolicy.validate:  # if validating, then no content would be created.
        return False

    if import_policy == TMLImportPolicy.all_or_none:
        return all([not r.is_error for r in results])  # if any of the results weren't an error, return true.

    if import_policy == TMLImportPolicy.partial:
        return any([not r.is_error for r in results])  # if any of the results weren't an error, return true.

    return False  # this should never happen, but just in case a new value is added.


def _remove_viz_guid(tml):
    attrs = _recursive_scan(tml, check=lambda attr: hasattr(attr, "viz_guid"))

    for liveboard_visualization in attrs:
        liveboard_visualization.viz_guid = None

    return tml