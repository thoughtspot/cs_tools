"""
This file contains the methods to execute the 'scriptability import' command.
"""
import click
import copy
import json
import pathlib
import time
import traceback

from httpx import HTTPStatusError
from rich.table import Table
from typer import Argument as A_, Option as O_  # noqa
from typing import Dict, List, Optional, Tuple, Union

from thoughtspot_tml.utils import determine_tml_type
from thoughtspot_tml.types import TMLObject

from cs_tools.cli.ux import console
from cs_tools.data.enums import AccessLevel, ConnectionType, GUID, TMLImportPolicy, StatusCode, MetadataObject
from cs_tools.errors import CSToolsError
from cs_tools.thoughtspot import ThoughtSpot
from .util import GUIDMapping, MetadataTypeList, TMLFileBundle, get_guid_from_filename


class TMLResponseReference:
    """
    Keeps track of the TML object including status of upload.
    """

    def _init_(self):
        self.status_code: StatusCode = StatusCode.unknown
        self.guid: GUID = None
        self.name: str = ""
        self.type = None
        self.metadata_type = None
        self.original_guid: GUID = None
        self.error_code: str = ""
        self.error_message: str = ""


def import_(
        ctx: click.Context,
        path: pathlib.Path = A_(
            ...,
            help='full path to the TML file or directory to import.',
            metavar='FILE_OR_DIR',
            dir_okay=True,
            resolve_path=True
        ),
        import_policy: TMLImportPolicy = O_(TMLImportPolicy.validate_only.value,
                                            help="The import policy type"),
        force_create: bool = O_(False,
                                help="If true, will force a new object to be created."),
        guid_file: Optional[pathlib.Path] = O_(
            None,
            help='Existing or new mapping file to map GUIDs from source instance to target instance.  '
                 'This file must conform with the GUID mapping structure defined in the thoughtspot_tml library.',
            metavar='JSON_FILE',
            dir_okay=False,
            resolve_path=True
        ),
        from_env: str = O_(None,
                           help="The environment name importing from, for GUID mapping."),
        to_env: str = O_(None,
                           help="The environment name importing to, for GUID mapping."),
        tags: List[str] = O_([], metavar='TAGS',
                             help='One or more tags to add to the imported content.'),
        share_with: List[str] = O_([], metavar='GROUPS',
                                   help='One or more groups to share the uploaded content with.'),
        tml_logs: Optional[pathlib.Path] = O_(
            None,
            help='full path to the directory to log sent TML.  TML can change during load.',
            metavar='DIR',
            dir_okay=True,
            resolve_path=True
        ),
        org: Union[str, int] = O_(None, help='Name or ID of org to import to.  The user must have access to that org.')
):
    """
    Import TML from a file or directory into ThoughtSpot.
    """
    ts = ctx.obj.thoughtspot

    if org:
        # ts.api.session.orgs_put(ts.org.lookup_id_for_name(org_name=org))
        ts.session.switch_org(org=org)

    if not path.exists():
        raise CSToolsError(error=f"{path} doesn't exist",
                           reason="You can only import from an existing directory.",
                           mitigation="Check the --path argument to make sure it is correct.")

    if tml_logs and not tml_logs.is_dir():
        raise CSToolsError(error=f"{path} doesn't exist",
                           reason="The logging directory must already exist.",
                           mitigation="Check the --tml_logs argument to make sure it is correct.")

    guid_mapping: Union[GUIDMapping, None] = None
    if guid_file:
        if not (from_env and to_env):
            raise CSToolsError(error=f"GUID files also require specifying the 'from' and 'to' environments.",
                               reason="Insufficient information to perform GUID mapping.",
                               mitigation="Set the --from-env and --to-env values.")
        else:
            guid_mapping = GUIDMapping(from_env=from_env, to_env=to_env, path=guid_file)

    if path.is_dir():  # individual files are listed as they are loaded so just show directory.
        if import_policy == TMLImportPolicy.validate_only:
            console.log(f"[bold green]validating from {path}.[/]")
        else:
            console.log(f"[bold green]importing from {path} with policy {import_policy.value}.[/]")

    if import_policy == TMLImportPolicy.validate_only:
        results = _import_and_validate(ts, path, force_create, guid_mapping, tml_logs)
    else:
        # results = _import_and_create(ts, path, import_policy, force_create, guid_mapping, tags, share_with, tml_logs)
        results = _import_and_create_bundle(ts, path, import_policy, force_create,
                                            guid_mapping, tags, share_with, tml_logs)

    _show_results_as_table(results)


def _import_and_validate(ts: ThoughtSpot, path: pathlib.Path, force_create: bool,
                         guid_mapping: GUIDMapping, tml_logs: pathlib.Path) -> Dict[GUID, Tuple]:
    """
    Does a validation import.  No content is created.  If FQNs map, they will be used.  If they don't, they will be
    removed.
    :param ts: The ThoughtSpot connection.
    :param path: Path to the directory or file.
    :param force_create: If true, all GUIDs are removed from content (but not FQNs that map)
    :param guid_mapping: The GUID mapping details.
    :param tml_logs: Directory to log imported content to.
    :returns: A dictionary with the results of the load.  The key is a GUID and the contents is a tuple with the
    (type, filename, and status) in that order.
    """
    results: Dict[GUID, Tuple] = {}

    all_tml_bundles = _load_tml_from_files(path)
    tml_file_bundles = {k: v for k, v in all_tml_bundles.items() if v.tml.tml_type_name != "connection"}

    connection_file_bundles= {k: v for k, v in all_tml_bundles.items() if v.tml.tml_type_name == "connection"}
    for cfb in connection_file_bundles.values():
        console.log(f'[bold yellow] Connection validation not supported.  Ignoring {cfb.file.name}')

    filenames = [tfb.file.name for tfb in tml_file_bundles.values()]

    # strip GUIDs if doing force create and convert to a list of TML string.
    if force_create:
        for _ in tml_file_bundles.values():
            _.tml.guid = None

    for f in filenames:
        console.log(f'validating {f}')

    with console.status(f"[bold green]importing {path.name}[/]"):
        tml_to_load = [_.tml.dumps() for _ in tml_file_bundles.values()]  # get the JSON to load

        if tml_logs:
            original_filenames = [tbf.file.name for tbf in tml_file_bundles.values()]
            fcnt = 0
            for tmlstr in tml_to_load:
                fn = f"{tml_logs}/{original_filenames[fcnt]}.imported"
                with open(fn, "w") as f:
                    f.write(tmlstr)
                fcnt += 1

        r = ts.api.metadata.tml_import(import_objects=tml_to_load,
                                       import_policy=TMLImportPolicy.validate_only.value,
                                       force_create=force_create)

        resp = _flatten_tml_response(r)

        fcnt = 0
        for _ in resp:
            try:
                if _.status_code == 'ERROR':
                    console.log(f"[bold red]{filenames[fcnt]} {_.status_code}: {_.error_message} ({_.error_code})[/]")
                    results[f"err-{fcnt}"] = ("", filenames[fcnt], StatusCode.error)
                elif _.status_code == 'WARNING':
                    console.log(
                        f"[bold yellow]{filenames[fcnt]} {_.status_code}: {_.error_message} ({_.error_code})[/]")
                    results[f"warn-{fcnt}"] = ("", filenames[fcnt], StatusCode.warning)
                else:
                    console.log(f"{filenames[fcnt]} {_.status_code}: {_.name} ({_.metadata_type}::{_.guid})")
                    results[_.guid] = (_.metadata_type, filenames[fcnt], StatusCode.ok)

            except KeyError as ke:
                console.log(f"Unexpected content: {_}")

            fcnt += 1

    return results


def _import_and_create_bundle(ts: ThoughtSpot, path: pathlib.Path, import_policy: TMLImportPolicy, force_create: bool,
                              guid_mapping: GUIDMapping, tags: List[str], share_with: List[str],
                              tml_logs: pathlib.Path) -> Dict[GUID, Tuple]:
    """
    Attempts to create new content.  If a mapping is not found, then an assumption is made that the mapping is correct.
    :param ts: The ThoughtSpot connection.
    :param path: Path to the directory or file.
    :param import_policy: The policy to either do all or none or the imports that fail.  Note that it's possible for
                          on level of the content to be successfully created an lower level content fail.
    :param force_create: If true, all GUIDs are removed from content (but not FQNs that map)
    :param guid_mapping: The GUID mapping between environments.
    :param tags: List of tags to apply.  Tags will be created if they don't exist.
    :param share_with: Shares with the groups of the given name, e.g. "Business Users"
    :param tml_logs: Directory to log uploaded TML to.
    :returns: A dictionary with the results of the load.  The key is a GUID and the contents is a tuple with the
    (type, filename, and status) in that order.
    """
    results: Dict[GUID, Tuple] = {}

    all_tml_bundles = _load_tml_from_files(path)  # all including connections.

    # split up by connection vs. not connection since connections use different APIs.
    tml_file_bundles: Dict[GUID, TMLFileBundle]
    connection_file_bundles: Dict[GUID, TMLFileBundle]

    tml_file_bundles = {k: v for k, v in all_tml_bundles.items() if v.tml.tml_type_name != "connection"}
    connection_file_bundles= {k: v for k, v in all_tml_bundles.items() if v.tml.tml_type_name == "connection"}

    all_resp = []
    all_results = {}

    try:

        # strip GUIDs if doing force create and convert to a list of TML string.
        if force_create:
            for _ in tml_file_bundles.values():
                _.tml.guid = None

        connection_tables: Dict[str, List[str]] = {}  # have to init in case there aren't any connections.
        with console.status(f"[bold green]importing {path.name}[/]"):
            # if there are connections, do those first.
            if connection_file_bundles:
                resp, results, connection_tables = _upload_connections(ts, guid_mapping, connection_file_bundles,
                                                                       tml_logs, import_policy, force_create)
                all_resp.extend(resp)
                all_results.update(results)

            # if there are TML, do those next.
            if tml_file_bundles:

                # If there were connections, new mapping may have been created.
                [guid_mapping.disambiguate(_.tml, delete_unmapped=True) for _ in tml_file_bundles.values()]

                resp, results = _upload_tml(ts, guid_mapping, tml_file_bundles,
                                            tml_logs, import_policy, force_create, connection_tables)
                all_resp.extend(resp)
                all_results.update(results)

    except Exception as e:  # just log the error and then let any content that got sent still get tagged and shared.
        console.log(f"[bold red]Error loading content: {e}")

    # responses for each item that didn't error.  Use for mapping and tagging.
    ok_resp = [_ for _ in all_resp if (_.status_code == StatusCode.ok or _.status_code == StatusCode.warning)]

    if guid_mapping:
        guid_mapping.save()

    if tags:
        _add_tags(ts, ok_resp, tags)

    if share_with:
        _share_with(ts, ok_resp, share_with)

    return all_results


def _load_tml_from_files(path: pathlib.Path) -> Dict[GUID, TMLFileBundle]:
    """
    Loads the TML files, returning a list of file names and the TML mapping from GUID to TML object.
    :param path: The path to the TML files (either a file or directory)
    :return: A dictionary of GUIDs to TML file bundles (path and TML object). Only files to be loaded will be included.
    """
    tml_file_bundles: Dict[GUID, TMLFileBundle] = {}

    if path.is_dir():
        for p in list(f for f in path.iterdir() if (f.match("*.tml") or f.match("*.yaml"))):
            if not p.is_dir():  # don't currently support sub-folders.  Might add later.
                _load_and_append_tml_file(path=p, tml_file_bundles=tml_file_bundles)
    else:
        _load_and_append_tml_file(path=path, tml_file_bundles=tml_file_bundles)

    log_bundle = [_.file.name for _ in tml_file_bundles.values()]
    console.log(f"Attempting to load: {log_bundle}")

    return tml_file_bundles


def _load_and_append_tml_file(
        path: pathlib.Path,
        tml_file_bundles: Dict[GUID, TMLFileBundle]) -> GUID:
    """
    Loads a TML file from the path, getting table mappings if needed.
    :param path:  The file path.
    :param tml_file_bundles: A mapping of GUID to a TML file and object.  Might get updated.
    :return: The GUID for the file or none if didn't get added
    """

    if path.is_dir():
        console.log(f"[error]Attempting to load a directory {path}.[/]")
        return None

    if not (path.name.endswith(".tml") or path.name.endswith(".yaml")):
        console.log(f"[bold red]{path} Only TML (.tml) and YAML (.yaml) files are supported.[/]")
        return None

    tmlobj = _load_tml_from_file(path=path)

    # If the GUID is not in the file, use the name.  This requires the first part of the name to be a GUID.
    # Connection YAML files don't have a GUID.
    if not hasattr(tmlobj, 'guid') or not tmlobj.guid:
        tmlobj.guid = path.name.split('.')[0]

    tml_file_bundles[tmlobj.guid] = TMLFileBundle(file=path, tml=tmlobj)

    return tmlobj.guid


def _load_tml_from_file(path: pathlib.Path) -> TMLObject:
    """
    Loads a TML object.  If it's a worksheet and the connection is provided, then the table FQNs will be modified.
    :param path: The path to the file.
    :return: A TML object.
    """
    tml_type = determine_tml_type(path=path)
    return tml_type.load(path)

#  The following was previous code that determined dependencies.  It may need to be revised, but will need updates
#  based on thoughtspot_tml changes.
# def _build_dependency_tree(tml_list: List[TML]) -> TSDependencyTree:
#      """
#      Builds a dependency tree for the TML to be loaded.
#      :param tml_list: List of TML to check.
#      :return: A dependency tree of content.  Loading can be done on the levels.
#      """
#      dt = TSDependencyTree()
#
#      for tml in tml_list:
#          depends_on = _find_depends_on(tml=tml.as_dict())
#          dt.add_dependency(tml.guid, depends_on=set(depends_on))
#
#      return dt
#
#
#  def _find_depends_on(tml: dict) -> List[str]:
#      """
#      Returns a list of dependencies for the TML.  These are identified by any FQNs in the file.
#      :param tml: The TML dictionary content (tml.tml)
#      :return: A list of FQNs this TML depends on.  Note that missing FQNs mean a dependency is ignored.
#      """
#      depends_on = []
#
#      for k in tml.keys():
#          #  print(f"{k} == {tml[k]}")
#          if k.lower() == "fqn":
#              depends_on.append(tml[k])
#          elif isinstance(tml[k], dict):
#              depends_on.extend(_find_depends_on(tml[k]))
#          elif isinstance(tml[k], list):
#              for _ in tml[k]:
#                  if isinstance(_, dict):
#                      depends_on.extend(_find_depends_on(_))
#
#      return depends_on


def _upload_connections(
    ts: ThoughtSpot,
    guid_mapping: GUIDMapping,
    connection_file_bundles: Dict[GUID, TMLFileBundle],
    tml_logs: pathlib.Path,
    import_policy: TMLImportPolicy,
    force_create: bool
) -> Tuple[List[TMLResponseReference], Dict[GUID, Tuple], Dict[str, List[str]]]:
    """
    Uploads connections.
    :param ts: The ThoughtSpot object.
    :param guid_mapping:  Mapping of old to new GUIDs.
    :param connection_file_bundles: The bundle of connections to upload.
    :param tml_logs: The TML log directory to log uploaded content.
    :param import_policy: The import policy to use.  Connections cannot be validated.
    :param force_create: If true, create new connections.  If false, try to update (might fail)
    :return: A tuple of responses, the results of the upload, a dictionary of connection and table names to de-dup.
    """

    resp: List[TMLResponseReference] = []
    results: Dict[GUID, Tuple] = {}
    connection_tables: Dict[str, List[str]] = {}  # connection name to table names

    if import_policy == TMLImportPolicy.validate_only:
        console.log("[bold yellow]Warning: connections don't support validate only policies.  Ignoring connections.[/]")
        return resp, results, connection_tables  # connection APIs don't support validate_only.

    if import_policy == TMLImportPolicy.all_or_none:
        console.log(f"[bold yellow]Warning: connections don't support 'ALL_OR_NONE' policies.  "
                    f"Using {TMLImportPolicy.partial.value} for connections.[/]")

    try:
        filenames = [tfb.file.name for tfb in connection_file_bundles.values()]

        #  connections have to be loaded one at a time.
        fcnt = 0
        for cnx_bundle in connection_file_bundles.values():

            try:
                cnx = cnx_bundle.tml

                # connections without passwords can be created, but then the following table create fails (and you
                # get errors in the UI.  So throw an exception to avoid future pain.
                password_found = False
                for p in cnx.connection.properties:
                    if p.key == "password" and p.value:
                        password_found = True
                        break

                if not password_found:
                    raise CSToolsError(error=f'Connection "{cnx.connection.name}" missing password',
                                       reason=f'Connections require a valid password to create tables.',
                                       mitigation='Add a password to the connection file and try again.')

                metadata = cnxtml_to_cnxjson(cnx.to_dict())

                if tml_logs:  # TODO - need to log after any changes, such as removing tables.
                    fn = f"{tml_logs}/{filenames[fcnt]}.imported"
                    fcnt += 1
                    with open(fn, "w") as f:
                        f.write(metadata)

                if force_create:

                    # If creating, and have tables in the connection and then create, you end up with the tables
                    # being created twice and the second time fails.  Delete the tables from the connection in these
                    # scenarios, so they get created from TML.  Not sure if older versions support this capability.
                    # This also requires the TML for tables be exported.
                    # HOWEVER, for connection updates, you have to have the tables.  This may be a bug.

                    # Currently descriptions aren't exported for connections, so they will be set to blank.
                    r = ts.api._connection.create(name=cnx.connection.name, description="",
                                                  type=ConnectionType.from_str(cnx.connection.type), createEmpty=True,
                                                  metadata=metadata)

                else:
                    # That was the original GUID, now we have to see if there is a mapping.
                    cnx.guid = guid_mapping.get_mapped_guid(cnx.guid)

                    r = ts.api._connection.update(name=cnx.name, description="", id=cnx.guid,
                                                  type=ConnectionType.from_str(cnx.connection.type), createEmpty=False,
                                                  metadata=metadata)

                tmlrr = TMLResponseReference()
                text = json.loads(r.text)
                if not r.is_error:
                    # for reasons known only to the creator, the create and update responses have slightly different
                    # responses.
                    if text.get('dataSource'):  # update if exists, create just has the details at the top level.
                        text = text.get('dataSource')

                    tmlrr.status_code = StatusCode.ok
                    tmlrr.guid = text['header']['id']
                    tmlrr.name = text['header']['name']
                    tmlrr.metadata_type = MetadataObject.data_source.value
                    resp.append(tmlrr)

                    # also need to add responses for each table that was created
                    table_list = []
                    for new_table in text.get('logicalTableList', []):
                        tname = new_table['header'].get('name')
                        tid = new_table['header'].get('id')
                        tmlrr = TMLResponseReference()
                        tmlrr.status_code = StatusCode.ok
                        tmlrr.guid = tid
                        tmlrr.name = tname
                        tmlrr.metadata_type = MetadataObject.logical_table.value
                        resp.append(tmlrr)

                        table_list.append(tname)

                    connection_tables[cnx.connection.name] = table_list

                    # need to write guid mappings to the file.
                    if guid_mapping:
                        old_table_guids = {}  # first get the old table GUIDs based on table name.
                        if cnx.connection.table:
                            for table in cnx.connection.table:
                                old_table_guids[table.name] = table.id

                        for new_table in text.get('logicalTableList', []):
                            tname = new_table['header'].get('name')
                            tid = new_table['header'].get('id')
                            if tname in old_table_guids.keys():
                                guid_mapping.set_mapped_guid(old_table_guids[tname], tid)
                            else:
                                console.log(f"Unexpected table returned from create: {tname} ({tid})")
                else:
                    tmlrr.status_code = r.status_code
                    tmlrr.error_code = "ERROR"
                    resp.append(tmlrr)

            except HTTPStatusError as e:
                console.log(f"[bold red]Failed to import {cnx_bundle.file.name}: {e.response.text}[/]")

        metadata_list = MetadataTypeList()

        fcnt = -1
        for _ in resp:
            # need to start at -1 because the last datasource can show up before the response is finished for tables.
            if _.metadata_type == MetadataObject.data_source.value:  # only update for data sources and not tables.
                fcnt += 1

            if _.status_code == 'ERROR':
                console.log(
                    f"[bold red]{filenames[fcnt]} {_.status_code}: {_.error_message} ({_.error_code})[/]")
                results[f"err-{fcnt}"] = ("unknown", filenames[fcnt], StatusCode.error)
            else:
                console.log(f"{filenames[fcnt]} {_.status_code}: {_.name} " f"({_.metadata_type}::{_.guid})")
                # if the object was loaded successfully and guid mappings are being used,
                # make sure the mapping is there
                if guid_mapping:
                    old_guid = get_guid_from_filename(filenames[fcnt])
                    guid_mapping.set_mapped_guid(old_guid, _.guid)
                results[_.guid] = (_.metadata_type, filenames[fcnt], StatusCode.ok)
                metadata_list.add(MetadataObject.data_source
                                  if _.metadata_type == MetadataObject.data_source.value
                                  else MetadataObject.logical_table,
                    _.guid)

        # connections are always partial, so wait for the ones that got created.
        _wait_for_metadata(ts=ts, metadata_list=metadata_list)

    except CSToolsError:
        raise  # just reraise so this process fails.
    except Exception as e:
        console.log(f"[bold red]{e}[/]")
        traceback.print_exc()

    return resp, results, connection_tables


def _upload_tml(
        ts: ThoughtSpot,
        guid_mapping: GUIDMapping,
        tml_file_bundles: Dict[GUID, TMLFileBundle],
        tml_logs: pathlib.Path,
        import_policy: TMLImportPolicy,
        force_create: bool,
        connection_tables: Dict[str, List[str]]
) -> Tuple[List[TMLResponseReference], Dict[GUID, Tuple]]:

    resp: List[TMLResponseReference] = []
    results: Dict[GUID, Tuple] = {}

    # if there were connections, then we need to exclude tables that were part of the connection.
    updated_file_bundles = {}
    if connection_tables:  # don't bother if no connections.
        for k, v in tml_file_bundles.items():
            if v.tml.tml_type_name == 'table':  # is this an enum somewhere?
                # see if the table and connection are in the TML
                connection_name = v.tml.table.connection.name
                table_name = v.tml.table.name
                if not (connection_name in connection_tables.keys() and
                        table_name in connection_tables[connection_name]):
                    updated_file_bundles[k] = v
            else:
                updated_file_bundles[k] = v
    else:  # no connections, so use the original.
        updated_file_bundles = copy.copy(tml_file_bundles)

    # No remaining TML, so just return with empty results.
    if not updated_file_bundles:
        return resp, results

    try:
        if guid_mapping:
            [guid_mapping.disambiguate(_.tml) for _ in updated_file_bundles.values()]
        tml_to_load = [_.tml.dumps() for _ in updated_file_bundles.values()]  # get the JSON to load

        filenames = [tfb.file.name for tfb in updated_file_bundles.values()]
        old_guids = [_ for _ in updated_file_bundles.keys()]  # keys and values return in the same order

        if tml_logs:
            fcnt = 0

            for tmlstr in tml_to_load:
                fn = f"{tml_logs}/{filenames[fcnt]}.imported"
                with open(fn, "w") as f:
                    f.write(tmlstr)
                fcnt += 1

        r = ts.api.metadata.tml_import(import_objects=tml_to_load,
                                       import_policy=import_policy.value,
                                       force_create=force_create)
        resp = _flatten_tml_response(r)

        metadata_list = MetadataTypeList()

        fcnt = 0  # keeps track of content to file loaded.
        error_free = True  # needed to see if there were errors.  If using ALL_OR_NONE, an error will cause no creation.
        guids_to_map = {}  # list of GUIDs to map.  GUIDs will only be added if the content was successfully loaded.

        for _ in resp:
            if _.status_code == StatusCode.error:
                error_free = False
                console.log(
                    f"[bold red]{filenames[fcnt]} {_.status_code}: {_.error_message} ({_.error_code})[/]")
                results[f"err-{fcnt}"] = ("unknown", filenames[fcnt], StatusCode.error)
            elif _.status_code == StatusCode.warning:
                console.log(f"[bold yellow]{filenames[fcnt]} {_.status_code}: {_.error_message} ({_.error_code})[/]")
                results[_.guid] = (_.metadata_type, filenames[fcnt], StatusCode.warning)
                old_guid = old_guids[fcnt]
                guids_to_map[old_guid] = _.guid
                metadata_list.add(
                    ts.metadata.tml_type_to_metadata_object(updated_file_bundles[old_guid].tml.tml_type_name),
                    _.guid)
            elif _.status_code == StatusCode.ok:
                console.log(f"{filenames[fcnt]} {_.status_code}: {_.name} " f"({_.metadata_type}::{_.guid})")
                # if the object was loaded successfully and guid mappings are being used,
                # make sure the mapping is there
                old_guid = old_guids[fcnt]
                guids_to_map[old_guid] = _.guid
                results[_.guid] = (_.metadata_type, filenames[fcnt], StatusCode.ok)
                metadata_list.add(
                    ts.metadata.tml_type_to_metadata_object(updated_file_bundles[old_guid].tml.tml_type_name),
                    _.guid)

            fcnt += 1

        # if the import policy is all or none and there was an error, then nothing should have gotten created.
        if import_policy != TMLImportPolicy.all_or_none or error_free:
            # was some success, so add the mappings to be saved.
            if guid_mapping:
                for k, v in guids_to_map.items():
                    guid_mapping.set_mapped_guid(k, v)
            _wait_for_metadata(ts=ts, metadata_list=metadata_list)
        else:  # need to not return the OK ones in this scenario because they would attempt to be tagged and shared.
            console.log('\n[bold yellow]Warning:  Content was not created.  This can be due to a failure when '
                        'using ALL_OR_NONE policy.[\]\n')
            resp = []

    except Exception as e:
        console.log(f"[bold red]{e}[/]")
        raise

    return resp, results


def _flatten_tml_response(r: Dict) -> [TMLResponseReference]:
    """
    Flattens a response to return key fields as an array of dictionaries for easier use.
    :param r: The response as a JSON object.
    :return: An array of individual responses objects.
      Keys for success are: status_code, guid, name, type, metadata_type
      Keys for error are: status_code, error_code, error_message
    """
    flat = []

    text = json.loads(r.text)
    if text:
        for _ in text['object']:
            trr = TMLResponseReference()
            trr.status_code = StatusCode.from_str(_['response']['status']['status_code'])
            if trr.status_code == StatusCode.ok:
                h = _['response']['header']
                trr.guid = h.get('id_guid', 'UNKNOWN')
                trr.name = h.get('name', 'UNKNOWN')
                trr.type = h.get('type', 'UNKNOWN')
                trr.metadata_type = h.get('metadata_type', 'UNKNOWN')
            elif trr.status_code == StatusCode.error:
                status = _['response']['status']
                trr.error_code = status.get('error_code', '')
                trr.error_message = status['error_message'].replace('<br/>', '')
            elif trr.status_code == StatusCode.warning:
                h = _['response']['header']
                status = _['response']['status']
                trr.error_code = status.get('status_code', '')
                trr.guid = h.get('id_guid', 'UNKNOWN')
                trr.error_message = status['error_message'].replace('<br/>', '')
                trr.name = h.get('name', 'UNKNOWN')
                trr.type = h.get('type', 'UNKNOWN')
                trr.metadata_type = h.get('metadata_type', 'UNKNOWN')
            else:
                h = _['response']['header']
                trr.guid = h.get('id_guid', 'UNKNOWN')
                trr.name = h.get('name', 'UNKNOWN')
                trr.type = h.get('type', 'UNKNOWN')
                trr.metadata_type = h.get('metadata_type', 'UNKNOWN')

            flat.append(trr)

    return flat


def _add_tags(ts: ThoughtSpot, objects: List[TMLResponseReference], tags: List[str]) -> None:
    """
    Adds the tags to the items in the response.
    :param ts: The ThoughtSpot object.
    :param objects: List of the objects to add the tags to.
    :param tags: List of tags to create.
    """
    with console.status(f"[bold green]adding tags: {tags}[/]"):
        ids = []
        types = []
        for _ in objects:
            ids.append(_.guid)
            types.append(_.metadata_type)
        if ids:  # might all be errors
            console.log(f'Adding tags {tags} to {ids}')
            try:
                ts.api.metadata.assigntag(id=ids, type=types, tagname=tags)
            except Exception as e:
                console.log(f'[bold red]Error adding tags: {e}.[/]')
                console.log(f'[bold red]Check spelling of the tag.[/]')


def _share_with(ts: ThoughtSpot, objects: List[TMLResponseReference], share_with: List[str]) -> None:
    """
    Shares the objects with the groups.
    :param ts: The ThoughtSpot interface object.
    :param objects: Objects to share with.
    :param share_with: The list of group names to share with.
    :return:
    """
    with console.status(f"[bold green]sharing with: {share_with}[/]"):
        groups = []
        for _ in share_with:
            try:
                groups.append(ts.group.get_group_id(_))
            except HTTPStatusError as e:
                console.log(f"[bold red]unable to get ID for group {_}: {e}")

        if groups:  # make sure some mapped

            # Bundling by type to save on calls.
            type_bundles = {}
            for _ in objects:
                if _.metadata_type == MetadataObject.data_source.value:  # connections don't support sharing as-of 8.9
                    continue

                guid_list = type_bundles.get(_.metadata_type, [])
                if not guid_list:
                    type_bundles[_.metadata_type] = guid_list
                guid_list.append(_.guid)

            permissions = {}
            for g in groups:
                permissions[g] = AccessLevel.read_only

            for ctype in type_bundles.keys():
                objectids = type_bundles[ctype]
                try:
                    ts.api.security.share(type=ctype, id=objectids, permissions=permissions)
                except HTTPStatusError as e:
                    console.log(f"Unable to share {objectids} of type {ctype} with permissions: {permissions}")


def _wait_for_metadata(ts: ThoughtSpot, metadata_list: MetadataTypeList):
    """
    This call will wait for metadata to be created.  This is needed when creating content that relies on
    recently created content.  It will eventually time out with an error after minute.
    :param metadata_list: A metadata list.
    :return:
    """

    # somewhat arbitrary wait times.  Don't go beyond a minute.
    wait_time_secs = 3
    max_wait_time_secs = 60

    total_waited_secs = 0
    items_to_wait_on = copy.copy(metadata_list)  # don't look for all the items every time.

    while not items_to_wait_on.is_empty() and total_waited_secs < max_wait_time_secs:
        console.log(f"Waiting on {items_to_wait_on} for {wait_time_secs} seconds.".replace('[', r'\['))
        # always sleep first since the first call will (probably) be immediately.
        time.sleep(wait_time_secs)
        total_waited_secs += wait_time_secs

        for ctype in items_to_wait_on.types():
            guids = items_to_wait_on.guids_for_type(metadata_type=ctype)
            existence = ts.metadata.objects_exist(metadata_type=ctype, guids=guids)
            for k, v in existence.items():  # guid -> bool
                if v:  # it exists
                    items_to_wait_on.remove(ctype, k)

    if not items_to_wait_on.is_empty():
        raise CSToolsError(error=f"Timing out on API call after {total_waited_secs} seconds",
                           reason=f"Exceeded timeout on items: {items_to_wait_on}",
                           mitigation=f"Check the connection and content to identify the issue.")

    # HACK ALERT!  It seems like you can create content and get confirmation it exists, but then it doesn't completely.
    time.sleep(3)


def _show_results_as_table(results: Dict[GUID, Tuple]) -> None:
    """
    Writes a pretty results table to the console.
    :param results: A dictionary with the results of the load.  The key is a GUID and the contents is a tuple with the
    (type, filename, and status) in that order.
    """
    table = Table(title="Import Results")

    # table.add_column("GUID", no_wrap=True)  <- Not showing GUID to reduce table width.
    table.add_column("Filename", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Type", no_wrap=True)

    for k in results:
        v = results[k]
        # Not displaying the GUID
        # guid = 'N/A' if k.startswith('err') else k

        # table.add_row(guid, v[1], v[2], v[0])
        table.add_row(str(v[1]), str(v[2]), str(v[0]))  # make sure all are strings.

    console.print(table)


def cnxtml_to_cnxjson (cnxtml: Dict) -> str:
    """
    Converts from the YAML/TML you get from downloading the YAML to the connection JSON metadata format.  See
    https://developers.thoughtspot.com/docs/?pageid=connections-api#connection-metadata for details on the format.
    :param cnxtml: The TML for the connection.
    :return: A str of the json.
    """
    cnxjson = {}

    # Example YAML
    """
    name: Retail Banking - TML Imported
    type: RDBMS_SNOWFLAKE
    authentication_type: SERVICE_ACCOUNT
    properties:
    - key: accountName
      value: thoughtspot_partner
    - key: user
      value: se_demo
    - key: password
      value: ""
    - key: role
      value: se_role
    - key: warehouse
      value: SE_DEMO_WH
    - key: database
      value: RETAIL_BANKING_V1_1
    table:
    - name: dim_rb_customers
      id: 250c5781-027a-4a26-a029-5322c5091200
      external_table:
        db_name: RETAIL_BANKING_V1_1
        schema_name: PUBLIC
        table_name: dim_rb_customers
      column:
      - name: customer_id
        id: 786afd22-9c16-4235-9b3e-7a2be21352ba
        data_type: INT64
        external_column: customer_id
      - name: customer_name
        id: 1171b434-2b35-4caa-9c68-4e597bfee7c1
        data_type: VARCHAR
        external_column: customer_name
      - name: gender
        id: 91733fca-00bc-4094-a871-04492746612b
        data_type: VARCHAR
        external_column: gender
    """

    # Example metadata.
    """
    {
       "configuration":{
          "accountName":"thoughtspot_partner",
          "user":"tsadmin",
          "password":"TestConn123",
          "role":"sysadmin",
          "warehouse":"MEDIUM_WH"
       },
       "externalDatabases":[
          {
             "name":"AllDatatypes",
             "isAutoCreated":false,
             "schemas":[
                {
                   "name":"alldatatypes",
                   "tables":[
                      {
                         "name":"allDatatypes",
                         "type":"TABLE",
                         "description":"",
                         "selected":true,
                         "linked":true,
                         "columns":[
                            {
                               "name":"CNUMBER",
                               "type":"INT64",
                               "canImport":true,
                               "selected":true,
                               "isLinkedActive":true,
                               "isImported":false,
                               "tableName":"allDatatypes",
                               "schemaName":"alldatatypes",
                               "dbName":"AllDatatypes"
                            },
                            {
                               "name":"CDECIMAL",
                               "type":"INT64",
                               "canImport":true,
                               "selected":true,
                               "isLinkedActive":true,
                               "isImported":false,
                               "tableName":"allDatatypes",
                               "schemaName":"alldatatypes",
                               "dbName":"AllDatatypes"
                            }
                         ]
                      }
                   ]
                }
             ]
          }
       ]
    }
    """

    # properties become part of the configuration
    configuration = {}
    for p in cnxtml['properties']:
        configuration[p['key']] = p['value']

    cnxjson['configuration'] = configuration
    cnxjson['externalDatabases'] = []  # default to empty.

    # first, organize tables by database and schema
    # { database_name: { schema_name: { table_name: [ columns ], table_name: [ columns ], ... } } }
    databases = {}
    if cnxtml.get('table', None):
        for t in cnxtml.get('table'):
            # all tables should have these or it should fail.
            db_name = t['external_table']['db_name']
            schema_name = t['external_table']['schema_name']
            table_name = t['external_table']['table_name']

            # columns are optional
            columns = []
            for c in t.get('column'):
                columns.append({
                    "name": c['external_column'],
                    "type": c['data_type'],
                    # using defaults for the following booleans since it's unknown.
                    "canImport": "true",
                    "selected": "true",
                    "isLinkActivated": "true",
                    "isImported": "false",
                    "tableName": table_name,
                    "schemaName": schema_name,
                    "dbName": db_name,
                })

            # at this point the details of a table should be known and need to be added to the appropriate DB
            db = databases.get(db_name) if db_name in databases.keys() else {}
            databases[db_name] = db

            schema = db.get(schema_name) if schema_name in db.keys() else {}  # tables and columns
            db[schema_name] = schema

            table = schema.get(table_name) if table_name in schema.keys() else []  # list of columns
            table.extend(columns)
            schema[table_name] = table

    # Convert to a proper metadata format now that things are combined.
    external_databases = []
    for dbn in databases.keys():
        db = databases.get(dbn)
        extdb = {
            "name": dbn,
            "isAutoCreated": "false",  # just defaulting to no.
        }
        schemas = []
        for sn in db.keys():  # keys for the db object are schemas.
            tables = []
            for tn in db[sn].keys():  # now get the tables for the schema
                t = db[sn][tn]
                table = {
                    "name": tn,
                    "type": "TABLE",
                    "description": "",  # is this available?   TODO verify and add.
                    "selected": "true",
                    "linked": "true",
                }
                columns = []
                for c in t:
                    columns.append({
                        "name": c.get("name"),
                        "type": c.get("type"),
                        "canImport": c.get("canImport", "true"),
                        "selected": c.get("selected", "true"),
                        "isLinkedActive": c.get("isLinkedActive", "true"),
                        "isImported": c.get("isImported", "false"),
                        "tableName": tn,
                        "schemaName": sn,
                        "dbName": dbn
                    })
                table["columns"] = columns
                tables.append(table)
            schemas.append({
                "name": sn,
                "tables": tables
            })
        extdb["schemas"] = schemas
        external_databases.append(extdb)

    cnxjson["externalDatabases"] = external_databases

    return json.dumps(cnxjson)
