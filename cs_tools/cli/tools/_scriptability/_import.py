"""
This file contains the methods to execute the 'scriptability import' command.
"""
import copy
import json
import pathlib
import time
from typing import Dict, List, Optional, Tuple

import click
import toml
from rich.table import Table
from thoughtspot_tml import YAMLTML
from thoughtspot_tml.tml import TML
from typer import Argument as A_, Option as O_  # noqa

from cs_tools.cli.types import CommaSeparatedValuesType
from cs_tools.cli.util import TSDependencyTree
from cs_tools.cli.ux import console
from cs_tools.data.enums import AccessLevel, GUID, TMLImportPolicy, TMLContentType, StatusCode
from cs_tools.errors import CSToolsError
from cs_tools.thoughtspot import ThoughtSpot
from ._create_mapping import create_guid_file_if_not_exists
from .util import MetadataTypeList, TMLFileBundle


class TMLResponseReference:
    """
    Keeps track of the TML object including status of upload.
    """

    def _init_(self):
        self.status_code = StatusCode.unknown
        self.guid = None
        self.name = None
        self.type = None
        self.metadata_type = None
        self.original_guid = None
        self.error_code = None
        self.error_message = None


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
            help='Existing or new mapping file to map GUIDs from source instance to target instance.',
            metavar='FILE_OR_DIR',
            dir_okay=False,
            resolve_path=True
        ),
        tags: List[str] = O_([], metavar='TAGS',
                             callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
                             help='One or more tags to add to the imported content.'),
        share_with: List[str] = O_([], metavar='GROUPS',
                                   callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
                                   help='One or more groups to share the uploaded content with.'),
        tml_logs: Optional[pathlib.Path] = O_(
            None,
            help='full path to the directory to log sent TML.  TML can change during load.',
            metavar='DIR',
            dir_okay=True,
            resolve_path=True
        ),
):
    """
    Import TML from a file or directory into ThoughtSpot.
    """
    ts = ctx.obj.thoughtspot

    if not path.exists():
        raise CSToolsError(error=f"{path} doesn't exist",
                           reason="You can only import from an existing directory.",
                           mitigation="Check the --path argument to make sure it is correct.")

    if tml_logs and not tml_logs.is_dir():
        raise CSToolsError(error=f"{path} doesn't exist",
                           reason="The logging directory must already exist.",
                           mitigation="Check the --tml_logs argument to make sure it is correct.")

    if path.is_dir():  # individual files are listed as they are loaded so just show directory.
        if import_policy == TMLImportPolicy.validate_only:
            console.log(f"[bold green]validating from {path}.[/]")
        else:
            console.log(f"[bold green]importing from {path} with policy {import_policy.value}.[/]")

    if import_policy == TMLImportPolicy.validate_only:
        results = _import_and_validate(ts, path, force_create, guid_file, tml_logs)
    else:
        # results = _import_and_create(ts, path, import_policy, force_create, guid_file, tags, share_with, tml_logs)
        results = _import_and_create_bundle(ts, path, import_policy, force_create,
                                            guid_file, tags, share_with, tml_logs)

    _show_results_as_table(results)


def _import_and_validate(ts: ThoughtSpot, path: pathlib.Path, force_create: bool,
                         guid_file: pathlib.Path, tml_logs: pathlib.Path) -> Dict[GUID, Tuple]:
    """
    Does a validation import.  No content is created.  If FQNs map, they will be used.  If they don't, they will be
    removed.
    :param ts: The ThoughtSpot connection.
    :param path: Path to the directory or file.
    :param force_create: If true, all GUIDs are removed from content (but not FQNs that map)
    :param guid_file: The file of GUID mappings.
    :param tml_logs: Directory to log imported content to.
    :returns: A dictionary with the results of the load.  The key is a GUID and the contents is a tuple with the
    (type, filename, and status) in that order.
    """
    results: Dict[GUID, Tuple] = {}
    guid_mappings: Dict[GUID: GUID] = _read_guid_mappings(guid_file=guid_file) if guid_file else {}

    tml_file_bundles = _load_tml_from_files(path, guid_mappings, delete_unmapped_fqns=True)
    filenames = [tfb.file.name for tfb in tml_file_bundles.values()]

    # strip GUIDs if doing force create and convert to a list of TML string.
    if force_create:
        [_.tml.remove_guid() for _ in tml_file_bundles.values()]

    for f in filenames:
        console.log(f'validating {f}')

    ok_resp = []  # responses for each item that didn't error.  Use for mapping and tagging.
    with console.status(f"[bold green]importing {path.name}[/]"):
        tml_to_load = [YAMLTML.dump_tml_object(tbf.tml) for tbf in tml_file_bundles.values()]

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
            if _.status_code == 'ERROR':
                console.log(f"[bold red]{filenames[fcnt]} {_.status_code}: {_.error_message} ({_.error_code})[/]")
                results[f"err-{fcnt}"] = ("unknown", filenames[fcnt], _.status_code)
            else:
                console.log(f"{filenames[fcnt]} {_.status_code}: {_.name} ({_.metadata_type}::{_.guid})")
                results[_.guid] = (_.metadata_type, filenames[fcnt], _.status_code)

            ok_resp.append(_)
            fcnt += 1

    return results


def _import_and_create_bundle(ts: ThoughtSpot, path: pathlib.Path, import_policy: TMLImportPolicy, force_create: bool,
                              guid_file: pathlib.Path, tags: List[str], share_with: List[str],
                              tml_logs: pathlib.Path) -> Dict[GUID, Tuple]:
    """
    Attempts to create new content.  If a mapping is not found, then an assumption is made that the mapping is correct.
    :param ts: The ThoughtSpot connection.
    :param path: Path to the directory or file.
    :param import_policy: The policy to either do all or none or the imports that fail.  Note that it's possible for
                          on level of the content to be successfully created an lower level content fail.
    :param force_create: If true, all GUIDs are removed from content (but not FQNs that map)
    :param guid_file: The file of GUID mappings.
    :param tags: List of tags to apply.  Tags will be created if they don't exist.
    :param share_with: Shares with the groups of the given name, e.g. "Business Users"
    :param tml_logs: Directory to log uploaded TML to.
    :returns: A dictionary with the results of the load.  The key is a GUID and the contents is a tuple with the
    (type, filename, and status) in that order.
    """
    results: Dict[GUID, Tuple] = {}
    guid_mappings: Dict[GUID: GUID] = _read_guid_mappings(guid_file=guid_file) if guid_file else {}

    tml_file_bundles = _load_tml_from_files(path, guid_mappings, delete_unmapped_fqns=True)

    # dt = _build_dependency_tree([tfb.tml for tfb in tml_file_bundles.values()])

    # strip GUIDs if doing force create and convert to a list of TML string.
    if force_create:
        [_.tml.remove_guid() for _ in tml_file_bundles.values()]

    # This is noisy.  Maybe add back later.
    # for f in files:
    #     console.log(f'{"validating" if import_policy == TMLImportPolicy.validate_only else "loading"} {f}')

    ok_resp = []  # responses for each item that didn't error.  Use for mapping and tagging.
    with console.status(f"[bold green]importing {path.name}[/]"):
        try:
            [_map_guids(tfb.tml, guid_mappings, False) for tfb in tml_file_bundles.values()]  # update GUIDs
            tml_to_load = [YAMLTML.dump_tml_object(_.tml) for _ in tml_file_bundles.values()]  # get the JSON to load

            filenames = [tfb.file.name for tfb in tml_file_bundles.values()]
            old_guids = [_ for _ in tml_file_bundles.keys()]  # keys and values return in the same order

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

            fcnt = 0
            for _ in resp:
                if _.status_code == 'ERROR':
                    console.log(
                        f"[bold red]{filenames[fcnt]} {_.status_code}: {_.error_message} ({_.error_code})[/]")
                    results[f"err-{fcnt}"] = ("unknown", filenames[fcnt], _.status_code)
                else:
                    console.log(f"{filenames[fcnt]} {_.status_code}: {_.name} " f"({_.metadata_type}::{_.guid})")
                    # if the object was loaded successfully and guid mappings are being used,
                    # make sure the mapping is there
                    old_guid = old_guids[fcnt]
                    if guid_file:
                        guid_mappings[old_guid] = _.guid
                    ok_resp.append(_)
                    results[_.guid] = (_.metadata_type, filenames[fcnt], _.status_code)
                    metadata_list.add(
                        ts.metadata.tml_type_to_metadata_object(tml_file_bundles[old_guid].tml.content_type),
                        _.guid)

                fcnt += 1

            _wait_for_metadata(ts=ts, metadata_list=metadata_list)

        except Exception as e:
            console.log(f"[bold red]{e}[/]")

    if guid_file:
        _write_guid_mappings(guid_file=guid_file, guid_mappings=guid_mappings)

    if tags:
        _add_tags(ts, ok_resp, tags)

    if share_with:
        _share_with(ts, ok_resp, share_with)

    return results


# No longer loading based on dependencies (see _import_and_create_bundle).  But don't want to delete yet in case
# we discover edge cases that need the capabilities.
# def _import_and_create(ts: ThoughtSpot, path: pathlib.Path, import_policy: TMLImportPolicy, force_create: bool,
#                        guid_file: pathlib.Path, tags: List[str], share_with: List[str],
#                        tml_logs: pathlib.Path) -> Dict[GUID, Tuple]:
#     """
#     Attempts to create new content.  Content is created in phases based on dependency, worksheets before
#     liveboards, etc.  If a mapping is not found, then an assumption is made that the mapping is correct.
#     :param ts: The ThoughtSpot connection.
#     :param path: Path to the directory or file.
#     :param import_policy: The policy to either do all or none or the imports that fail.  Note that it's possible for
#                           on level of the content to be successfully created an lower level content fail.
#     :param force_create: If true, all GUIDs are removed from content (but not FQNs that map)
#     :param guid_file: The file of GUID mappings.
#     :param tags: List of tags to apply.  Tags will be created if they don't exist.
#     :param share_with: Shares with the groups of the given name, e.g. "Business Users"
#     :param tml_logs: Directory to log uploaded TML to.
#     :returns: A dictionary with the results of the load.  The key is a GUID and the contents is a tuple with the
#     (type, filename, and status) in that order.
#     """
#     results: Dict[GUID, Tuple] = {}
#     guid_mappings: Dict[GUID: GUID] = _read_guid_mappings(guid_file=guid_file) if guid_file else {}
#
#     tml_file_bundles = _load_tml_from_files(path, guid_mappings, delete_unmapped_fqns=False)
#
#     dt = _build_dependency_tree([tfb.tml for tfb in tml_file_bundles.values()])
#
#     # strip GUIDs if doing force create and convert to a list of TML string.
#     if force_create:
#         [_.tml.remove_guid() for _ in tml_file_bundles.values()]
#
#     # This is noisy.  Maybe add back later.
#     # for f in files:
#     #     console.log(f'{"validating" if import_policy == TMLImportPolicy.validate_only else "loading"} {f}')
#
#     ok_resp = []  # responses for each item that didn't error.  Use for mapping and tagging.
#     with console.status(f"[bold green]importing {path.name}[/]"):
#         try:
#
#             for level in dt.levels:
#                 if level:
#                     level_tml_bundles = [tml_file_bundles[guid] for guid in level]  # get the content for this level.
#                     [_map_guids(tfb.tml, guid_mappings, False) for tfb in level_tml_bundles]  # update GUIDs
#                     tml_to_load = [YAMLTML.dump_tml_object(_.tml) for _ in level_tml_bundles]  # get the JSON to load
#                     filenames = [tfb.file.name for tfb in level_tml_bundles]
#
#                     if tml_logs:
#                         fcnt = 0
#
#                         for tmlstr in tml_to_load:
#                             fn = f"{tml_logs}/{filenames[fcnt]}.imported"
#                             with open(fn, "w") as f:
#                                 f.write(tmlstr)
#                             fcnt += 1
#
#                     r = ts.api.metadata.tml_import(import_objects=tml_to_load,
#                                                    import_policy=import_policy.value,
#                                                    force_create=force_create)
#                     resp = _flatten_tml_response(r)
#
#                     metadata_list = MetadataTypeList()
#
#                     fcnt = 0
#                     for _ in resp:
#                         if _.status_code == 'ERROR':
#                             console.log(
#                                 f"[bold red]{filenames[fcnt]} {_.status_code}: {_.error_message} ({_.error_code})[/]")
#                             results[f"err-{fcnt}"] = ("unknown", filenames[fcnt], _.status_code)
#                         else:
#                             console.log(f"{level_tml_bundles[fcnt].file.name} {_.status_code}: {_.name} "
#                                         f"({_.metadata_type}::{_.guid})")
#                             # if the object was loaded successfully and guid mappings are being used,
#                             # make sure the mapping is there
#                             if guid_file:
#                                 guid_mappings[level[fcnt]] = _.guid
#                             ok_resp.append(_)
#                             results[_.guid] = (_.metadata_type, filenames[fcnt], _.status_code)
#                             metadata_list.add(
#                                 ts.metadata.tml_type_to_metadata_object(level_tml_bundles[fcnt].tml.content_type),
#                                 _.guid)
#
#                         fcnt += 1
#
#                     _wait_for_metadata(ts=ts, metadata_list=metadata_list)
#
#         except Exception as e:
#             console.log(f"[bold red]{e}[/]")
#
#     if guid_file:
#         _write_guid_mappings(guid_file=guid_file, guid_mappings=guid_mappings)
#
#     if tags:
#         _add_tags(ts, ok_resp, tags)
#
#     if share_with:
#         _share_with(ts, ok_resp, share_with)
#
#     return results


def _load_tml_from_files(path: pathlib.Path,
                         guid_mappings: Dict[GUID, GUID],
                         delete_unmapped_fqns) -> Dict[GUID, TMLFileBundle]:
    """
    Loads the TML files, returning a list of file names and the TML mapping from GUID to TML object.
    :param path: The path to the TML files (either a file or directory)
    :param guid_mappings: The mapping for for old to new GUIDs.
    :param delete_unmapped_fqns: If true, delete FQNs that are not mapped.  Usually only when validating new.
    :return: A dictionary of GUIDs to TML file bundles (path and TML object). Only files to be loaded will be included.
    """
    tml_file_bundles: Dict[GUID, TMLFileBundle] = {}

    if path.is_dir():
        for p in list(f for f in path.iterdir() if f.match("*.tml")):
            if not p.is_dir():  # don't currently support sub-folders.  Might add later.
                _load_and_append_tml_file(path=p,
                                          guid_mappings=guid_mappings, tml_file_bundles=tml_file_bundles,
                                          delete_unmapped_fqns=delete_unmapped_fqns)
    else:
        _load_and_append_tml_file(path=path,
                                  guid_mappings=guid_mappings, tml_file_bundles=tml_file_bundles,
                                  delete_unmapped_fqns=delete_unmapped_fqns)

    log_bundle = [_.file.name for _ in tml_file_bundles.values()]
    console.log(f"Attempting to load: {log_bundle}")

    return tml_file_bundles


def _read_guid_mappings(guid_file: pathlib.Path) -> Dict[GUID, TML]:
    """
    Reads the guid mapping file and creates a dictionary of old -> new mappings.  Note that the GUID file _must_ be
    a valid TOML file of the format used by the scriptability tool.
    :param guid_file: The path to a file that may or may not exist.
    :return: A mapping of old to new GUIDs.
    """
    create_guid_file_if_not_exists(guid_file=guid_file)

    try:
        toml_content = toml.load(str(guid_file))
        mappings = toml_content.get('mappings', {})
        if not mappings:
            console.log(f"[bold yellow]Warning: No mappings provided in {guid_file}.[/]")

        return mappings

    except toml.decoder.TomlDecodeError as err:
        raise CSToolsError(error=f"File decode error: {err}",
                           reason=f"Unable to load TOML from {guid_file}.",
                           mitigation=f"Check {guid_file} to make sure it's valid TOML format.")


def _write_guid_mappings(guid_file: pathlib.Path, guid_mappings) -> None:
    """
    Writes the GUID mappings out to the mapping file.
    :param guid_file:
    :param guid_mappings:
    """
    create_guid_file_if_not_exists(guid_file=guid_file)  # just to make sure.

    try:
        toml_content = toml.load(str(guid_file))
        toml_content["mappings"] = guid_mappings
        with open(guid_file, "w") as f:
            toml.dump(toml_content, f)

    except toml.decoder.TomlDecodeError as err:
        raise CSToolsError(error=f"File decode error: {err}",
                           reason=f"Unable to load TOML from {guid_file}.",
                           mitigation=f"Check {guid_file} to make sure it's valid TOML format.")
    except OSError as err:
        raise CSToolsError(error=f"File error: {err}",
                           reason=f"Unable to write to TOML file {guid_file}.",
                           mitigation=f"Check {guid_file} to make sure it's valid TOML format and writeable.")


def _load_and_append_tml_file(
        path: pathlib.Path,
        guid_mappings: Dict,
        tml_file_bundles: Dict[GUID, TMLFileBundle],
        delete_unmapped_fqns) -> GUID:
    """
    Loads a TML file from the path, getting table mappings if needed.
    :param path:  The file path.
    :param guid_mappings: The dictionary that maps from old GUID to new GUID.
    :param tml_file_bundles: A mapping of GUID to a TML file and object.  Might get updated.
    :param delete_unmapped_fqns: If true, GUIDs not in the mapping file will be deleted.
    :return: The GUID for the file or none if didn't get added
    """

    if path.is_dir():
        console.log(f"[error]Attempting to load a directory {path}.[/]")
        return None

    if not path.name.endswith(".tml"):
        console.log(f"[bold red]{path} Only TML (.tml) files are supported.[/]")
        return None

    tmlobj = _load_tml_from_file(path=path)

    _map_guids(tml=tmlobj, guid_mappings=guid_mappings, delete_unmapped_fqns=delete_unmapped_fqns)

    if tmlobj.content_type == TMLContentType.table.value:
        console.log(f"[bold red]Table import not currently supported.  Ignoring {path.name}.[/]")
        return None
    else:
        tml_file_bundles[tmlobj.guid] = TMLFileBundle(file=path, tml=tmlobj)

    return tmlobj.guid


def _load_tml_from_file(path: pathlib.Path) -> TML:
    """
    Loads a TML object.  If it's a worksheet and the connection is provided, then the table FQNs will be modified.
    :param path: The path to the file.
    :return: A TML object.
    """
    with open(path, "r") as tmlfile:
        tmlstr = tmlfile.read()

    return YAMLTML.get_tml_object(tml_yaml_str=tmlstr)


def _build_dependency_tree(tml_list: List[TML]) -> TSDependencyTree:
    """
    Builds a dependency tree for the TML to be loaded.
    :param tml_list: List of TML to check.
    :return: A dependency tree of content.  Loading can be done on the levels.
    """
    dt = TSDependencyTree()

    for tml in tml_list:
        depends_on = _find_depends_on(tml=tml.tml)
        dt.add_dependency(tml.guid, depends_on=set(depends_on))

    return dt


def _find_depends_on(tml: dict) -> List[str]:
    """
    Returns a list of dependencies for the TML.  These are identified by any FQNs in the file.
    :param tml: The TML dictionary content (tml.tml)
    :return: A list of FQNs this TML depends on.  Note that missing FQNs mean a dependency is ignored.
    """
    depends_on = []

    for k in tml.keys():
        #  print(f"{k} == {tml[k]}")
        if k.lower() == "fqn":
            depends_on.append(tml[k])
        elif isinstance(tml[k], dict):
            depends_on.extend(_find_depends_on(tml[k]))
        elif isinstance(tml[k], list):
            for _ in tml[k]:
                if isinstance(_, dict):
                    depends_on.extend(_find_depends_on(_))

    return depends_on


def _map_guids(tml: TML, guid_mappings: Dict, delete_unmapped_fqns: bool) -> TML:
    """
    Updates the TML to map any known GUIDs to new GUIDs.  If the old GUID (guid in file) is in the mapping as a key,
    it will be replaced with the value.
    :param tml: A TML object to replace mappings on.
    :param guid_mappings: The mapping dictionary of the form guid_mapping[<old_guid>] => <new_guid>
    :param delete_unmapped_fqns: If true, GUIDs and FQNs that don't have a mapping, will be deleted.
    """

    # check all entries in the tml to see if they are GUID or FQN.
    # If yes, try to change the value.
    # If no, try mapping, but at the next level down.  Ruturn when there are no child levels.
    _find_and_map_guids(tml=tml.tml, guid_mappings=guid_mappings, delete_unmapped_fqns=delete_unmapped_fqns)
    return tml


def _find_and_map_guids(tml: Dict, guid_mappings: Dict, delete_unmapped_fqns: bool) -> None:
    """
    Recursively finds GUIDs (GUID or fqn entries) and replaces if the GUID is mapped.  This shouldn't get too deep.
    :param tml: The TML fragment to check.
    :param guid_mappings: The mapping to use.
    :param delete_unmapped_fqns: If true, GUIDs and FQNs that don't have a mapping, will be deleted.
    """
    guid_key_names = ('guid', 'fqn')
    del_key = None
    for k in tml.keys():
        if k in guid_key_names:
            v = tml.get(k, None)
            if v:
                if v in guid_mappings.keys():  # if there is a mapping, replace it.
                    tml[k] = guid_mappings[v]
                # if there isn't a mapping and we are deleting unmapped, then delete the FQN.  Note that this checks
                # to verify the value hasn't been set on either side.
                elif delete_unmapped_fqns and k == 'fqn' and tml[k] not in guid_mappings.values():
                    del_key = k  # this works because there is only one FQN for a given dictionary.
        elif isinstance(tml[k], dict):
            _find_and_map_guids(tml=tml[k], guid_mappings=guid_mappings, delete_unmapped_fqns=delete_unmapped_fqns)
        elif isinstance(tml[k], list):
            for _ in tml[k]:
                if isinstance(_, dict):
                    _find_and_map_guids(tml=_, guid_mappings=guid_mappings, delete_unmapped_fqns=delete_unmapped_fqns)

    if del_key:
        del (tml[del_key])


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
            trr.status_code = _['response']['status']['status_code']
            if trr.status_code == 'OK':
                h = _['response']['header']
                trr.guid = h.get('id_guid', 'UNKNOWN')
                trr.name = h.get('name', 'UNKNOWN')
                trr.type = h.get('type', 'UNKNOWN')
                trr.metadata_type = h.get('metadata_type', 'UNKNOWN')
            else:
                status = _['response']['status']
                trr.error_code = status.get('error_code', '')
                trr.error_message = status['error_message'].replace('<br/>', '')

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
                console.log(f'[bold red]Error adding tags: {e}[/]')


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
            except Exception as e:
                console.log(f"[bold red]unable to get ID for group {_}: {e}")

        if groups:  # make sure some mapped

            # Bundling by type to save on calls.
            type_bundles = {}
            for _ in objects:
                guid_list = type_bundles.get(_.metadata_type, [])
                if not guid_list:
                    type_bundles[_.metadata_type] = guid_list
                guid_list.append(_.guid)

            permissions = {}
            for g in groups:
                permissions[g] = AccessLevel.read_only

            for ctype in type_bundles.keys():
                objectids = type_bundles[ctype]
                ts.api.security.share(type=ctype, id=objectids, permissions=permissions)


def _wait_for_metadata(ts: ThoughtSpot, metadata_list: MetadataTypeList):
    """
    This call will wait for metadata to be created.  This is needed when creating content that relies on
    recently created content.  It will eventually time out with an error after minute.
    :param metadata_list: A metadata list.
    :return:
    """

    # somewhat arbitrary wait times.  Don't go beyond a minute.
    wait_time_secs = 5
    max_wait_time_secs = 60

    total_waited_secs = 0
    items_to_wait_on = copy.copy(metadata_list)  # don't look for all the items every time.

    while not items_to_wait_on.is_empty() and total_waited_secs < max_wait_time_secs:
        console.log(f"Waiting on {items_to_wait_on} for {wait_time_secs} seconds.")
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
        table.add_row(v[1], v[2], v[0])

    console.print(table)
