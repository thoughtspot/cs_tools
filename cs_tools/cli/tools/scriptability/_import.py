"""
This file contains the methods to execute the 'scriptability import' command.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Union
import pathlib
import logging
import time
import copy
import re

from thoughtspot_tml.utils import determine_tml_type
from thoughtspot_tml.types import TMLObject
from rich.table import Table
from httpx import HTTPStatusError
import typer

from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.errors import CSToolsError
from cs_tools.cli.ux import rich_console
from cs_tools.cli.ux import CSToolsArgument as Arg
from cs_tools.cli.ux import CSToolsOption as Opt
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


def _mute_our_rich_handler() -> None:
    rich_handler = next(h for h in logging.getLogger().handlers if hasattr(h, "console") and h.console == rich_console)
    rich_handler.setLevel(logging.WARNING)


# class TMLResponseReference:
#     """
#     Keeps track of the TML object including status of upload.
#     """

#     def _init_(self):
#         self.status_code: StatusCode = StatusCode.unknown
#         self.guid: GUID = None
#         self.name: str = ""
#         self.type = None
#         self.metadata_type = None
#         self.original_guid: GUID = None
#         self.error_code: str = ""
#         self.error_message: str = ""


def to_import(
    ctx: typer.Context,
    path: pathlib.Path = Arg(
        ...,
        help="full path to the TML file or directory to import.",
        exists=True,
        resolve_path=True,
    ),
    import_policy: TMLImportPolicy = Opt(TMLImportPolicy.validate, help="the import policy type"),
    force_create: bool = Opt(False, help="if true, will force a new object to be created"),
    guid_file: pathlib.Path = Opt(
        None,
        help="existing or new mapping file to map GUIDs from source instance to target instance",
        dir_okay=False,
        resolve_path=True,
        rich_help_panel="GUID File Options",
    ),
    from_env: str = Opt(None, help="the environment name importing from", rich_help_panel="GUID File Options"),
    to_env: str = Opt(None, help="the environment name importing to", rich_help_panel="GUID File Options"),
    tags: List[str] = Opt(None, help="tags to add to the imported content"),
    share_with: List[str] = Opt(None, help="groups to share the uploaded content with"),
    tml_logs: pathlib.Path = Opt(
        None,
        help="full path to the directory to log sent TML. TML can change during load.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    org: Union[str, int] = Opt(None, help="name or ID of an Org to import to", hidden=True),
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

    ts = ctx.obj.thoughtspot

    if org is not None:
        ts.org.switch(org)

    log_fp = path / "tml_import.log" if tml_logs is not None else pathlib.Path("tml_import.log")
    log.setLevel(logging.INFO)
    log.addHandler(logging.FileHandler(log_fp.as_posix(), encoding="UTF-8", delay=True))

    guid_mapping = GUIDMapping(from_env=from_env, to_env=to_env, path=guid_file) if guid_file is not None else None

    if import_policy == TMLImportPolicy.validate:
        log.info(f"validating from {path}")
        results = _import_and_validate(ts, path, force_create, guid_mapping, tml_logs)

    else:
        log.info(f"importing from {path} with policy {import_policy}")
        results = _import_and_create_bundle(
            ts, path, import_policy, force_create, guid_mapping, tags, share_with, tml_logs
        )

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

        # strip GUIDs if doing force create and convert to a list of TML string.
        if force_create:
            tml_file.tml.guid = None

        if tml_logs is not None:
            filename = f"{tml_file.filepath.stem}.IMPORTED"
            tml_file.tml.dump(tml_logs / f"{filename}.{tml_file.tml.tml_type_name}.tml")

        log.info(f"validating {tml_file.filepath.name}")
        tml_files.append(tml_file)

    #
    #
    #

    with rich_console.status(f"[bold green]importing {path.name}[/]"):
        r = ts.api.metadata_tml_import(
            import_objects=[tml_file.tml.dumps() for tml_file in tml_files],
            import_policy=TMLImportPolicy.validate,
            force_create=force_create,
        )

        results: List[TMLImportResponse] = []

        for tml_file, content in zip(tml_files, r.json()["object"]):
            results.append(
                TMLImportResponse(
                    guid=content["response"].get("header", {}).get("id_guid", tml_file.tml.guid),
                    metadata_object_type=TMLSupportedContent[tml_file.tml.tml_type_name].value,
                    tml_type_name=tml_file.tml.tml_type_name,
                    name=tml_file.filepath.stem,
                    status_code=content["response"]["status"]["status_code"],
                    error_messages=content["response"]["status"].get("error_message", None),
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

    responses = []
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
                r, d, connection_tables = _upload_connections(**kw, connection_file_bundles=cnxn_files)
                responses.extend(r)
                results.extend(d)
            else:
                # connection name --> table names
                connection_tables: Dict[str, str] = {}

            if tml_files:
                r, d = _upload_tml(**kw, tml_file_bundles=tml_files, connection_tables=connection_tables)
                responses.extend(r)
                results.extend(d)

    # log the error, but let any content that got imported still get tagged and shared
    except Exception as e:
        log.error(f"error loading content: {e}, see logs for details..")
        log.debug(e, exc_info=True)

    if guid_mapping:
        guid_mapping.save()

    if tags:
        _add_tags(ts, [r for r in responses if not r.is_error], tags)

    if share_with:
        _share_with(ts, [r for r in responses if not r.is_error], share_with)

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

    log_bundle = ", ".join([tml_file.filepath.name for tml_file in tml_file_bundles])
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
            filename = f"{tml_file.filepath.stem}.IMPORTED"
            tml_file.tml.dump(tml_logs / f"{filename}.{tml_file.tml.tml_type_name}.tml")

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
            responses.append(
                TMLImportResponse(
                    guid=tml.guid,
                    metadata_object_type="DATA_SOURCE",
                    tml_type_name="connection",
                    name=tml.name,
                    status_code=r.reason_phrase,
                    error_messages=str(r.status_code),
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
                    status_code=r.reason_phrase,
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
                guid_mapping.set_mapped_guid(tml.guid, data["header"]["id"])

                old_table_guids = {t.name: t.id for t in tml.connection.tables}

                for table in data["logicalTableList"]:
                    old_guid = old_table_guids.get(table["header"]["name"])
                    new_guid = table["header"]["id"]
                    guid_mapping.set_mapped_guid(old_guid, new_guid)

    # CONNECTIONS ARE ALWAYS PARTIAL, WAIT FOR THE CREATED ONES
    _wait_for_metadata(ts=ts, metadata_list=[imported_object.guid for imported_object in responses])

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

        if tml_logs is not None:
            filename = f"{tml_file.filepath.stem}.IMPORTED"
            tml_file.tml.dump(tml_logs / f"{filename}.{tml_file.tml.tml_type_name}.tml")

    r = ts.api.metadata_tml_import(
        import_objects=[tml_file.tml.dumps() for tml_file in updated],
        import_policy=import_policy,
        force_create=force_create,
    )

    guids_to_map: Dict[GUID, GUID] = {}

    for tml_file, content in zip(updated, r.json()["object"]):
        guid = content["response"].get("header", {}).get("id_guid", tml_file.tml.guid)
        type = content["response"].get("header", {}).get("type", tml_file.tml.tml_type_name)
        name = content["response"].get("header", {}).get("name", tml_file.filepath.stem)

        if content["response"]["status"]["status_code"] == "OK":
            guids_to_map[tml_file.tml.guid] = guid

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

    is_error_free = all(r.is_success for r in responses)

    if is_error_free or import_policy != TMLImportPolicy.all_or_none:
        if guid_mapping is not None:
            for old_guid, new_guid in guids_to_map.items():
                guid_mapping.set_mapped_guid(old_guid, new_guid)

        _wait_for_metadata(ts=ts, metadata_list=[imported_object.guid for imported_object in responses])

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
            types.append(_.metadata_type)
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
                if _.metadata_type == MetadataObjectType.data_source:  # connections don't support sharing as-of 8.9
                    continue

                guid_list = type_bundles.get(_.metadata_type, [])
                if not guid_list:
                    type_bundles[_.metadata_type] = guid_list
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

        r_t = (ts.metadata_list(metadata_type="LOGICAL_TABLE", fetch_guids=list(guids), hidden=False),)
        r_a = (ts.metadata_list(metadata_type="QUESTION_ANSWER_BOOK", fetch_guids=list(guids), hidden=False),)
        r_p = (ts.metadata_list(metadata_type="PINBOARD_ANSWER_BOOK", fetch_guids=list(guids), hidden=False),)

        for response in (r_t, r_a, r_p):
            for header in response.json()["headers"]:
                ready_guids.add(header["id"])

        time.sleep(5.0)


def _show_results_as_table(results: List[TMLImportResponse]) -> None:
    """
    Writes a pretty results table to the rich_console.
    """
    table = Table(title="Import Results", width=150)

    table.add_column("Status", justify="center", width=10)  # 4 + length of literal: status
    # table.add_column("GUID", justify="center", width=40)     # 4 + length of a guid
    table.add_column("Type", no_wrap=True)
    table.add_column("Filename", no_wrap=True)

    for r in results:
        table.add_row(r.status_code, r.type_name, r.filename)

    rich_console.print(table)
