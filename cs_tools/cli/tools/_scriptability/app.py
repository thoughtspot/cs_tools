# DEV NOTE:
#
# Future enhancements:
#   - add support for GUID mapping across instances of ThoughtSpot
#   - ability to manipulate objects, such as renaming references to worksheets and tables, token replacement, etc.
#   - add support for tables and connections
#   - add support for importing .zip files
#

import json
import pathlib
import click
import toml
from thoughtspot_tml import YAMLTML
from thoughtspot_tml.tml import TML
from typer import Argument as A_, Option as O_  # noqa
from typing import Dict, List, Optional
import typer

from cs_tools.data.enums import AccessLevel, GUID, StatusCode, TMLImportPolicy, TMLType, TMLContentType
from cs_tools.cli.ux import console, CommaSeparatedValuesType, CSToolsCommand, CSToolsGroup
from cs_tools.cli.tools import common
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT

from . import __version__


def strip_blanks(inp: List[str]) -> List[str]:
    return [e for e in inp if e]


app = typer.Typer(
    help="""
    Tool for easily migrating TML between clusters.

    [b][yellow]USE AT YOUR OWN RISK![/b] This tool uses private API calls which
    could change on any version update and break the tool.[/]

    ThoughtSpot provides the ability to extract object metadata (tables, worksheets, liveboards, etc.) 
    in ThoughtSpot Modeling Language (TML) format, which is a text format based on YAML.  
    These files can then be modified and imported into another (or the same) instance to either create 
    or modify objects.

      cs_tools tools scriptability --help
    
    \f
    """,
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=common.setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def export(
        ctx: click.Context,
        path: pathlib.Path = A_(  # may not want to use
            ...,
            help='full path (directory) to save data set to',
            metavar='DIR',
            dir_okay=True,
            resolve_path=True
        ),
        tags: List[str] = O_([], metavar='TAGS',
                             callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
                             help='comma separated list of tags to export'),
        export_ids: List[str] = O_([], metavar='GUIDS',
                                   callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
                                   help='comma separated list of guids to export'),
        # consider JSON format in the future.  Not currently needed.
        # formattype: TMLType = O_(TMLType.yaml.value,
        #                  help=f'if specified, format to export, either {TMLType.yaml.value} or {TMLType.json.value}'),
        export_associated: bool = O_(False,
                                     help='if specified, also export related content'),
        set_fqns: bool = O_(False,
                            help='if set, then the content in the TML will have FQNs (GUIDs) added.')
):
    """
    Exports TML as YAML from ThoughtSpot.
    """
    if not path.is_dir():
        console.stderr(f"[bold red]Only directories are supported for export.  {path} is not a directory.[/]")
        raise typer.Exit(-1)

    ts = ctx.obj.thoughtspot
    export_ids = strip_blanks(export_ids)
    tags = strip_blanks(tags)

    # Scenarios to support
    # GUID/tags only - download the content and save
    # With associated - download content with associated and save
    # With fqns - download content with associated, map FQNs, save content specified (original or with FQNs)

    if tags:
        export_ids.extend(ts.metadata.get_object_ids_with_tags(tags))

    for id in export_ids:
        with console.status((f"[bold green]exporting {id} {'with' if export_associated else 'without'}"
                             f"associated content.[/]")):

            r = ts.api.metadata.tml_export(export_ids=[id],  # only doing one at a time to account for FQN mapping
                                           formattype=TMLType.yaml.value,  # formattype=formattype
                                           export_associated=(export_associated or set_fqns))

            objects = r.json().get('object', [])
            tml_objects = []
            for _ in objects:
                status = _['info']['status']
                if not status['status_code'] == 'OK':  # usually access errors.
                    console.log(f"[bold red]unable to get {_['info']['name']}: {_['info']['status']}[/]")

                else:
                    console.log(f"{_['info']['filename']} (OK)")
                    tmlobj = YAMLTML.get_tml_object(tml_yaml_str=_['edoc'])
                    tml_objects.append(tmlobj)

            if set_fqns:
                # getting associated, this will also get the additional FQNs for the objects and add to the TML.
                _add_fqns_to_tml(tml_list=tml_objects)

            # if the export_associated was specified, write all, else just write the requested.
            for _ in filter(lambda tml: export_associated or tml.guid == id, tml_objects):
                _write_tml_obj_to_file(path=path, tml=_)


def _add_fqns_to_tml(tml_list: List[TML]) -> None:
    """
    Looks up and adds the FQNs to the TML content.
    :param tml_list: List of TML types.
    """

    # First map all the names to GUIDs.  Names should be unique if starting with a single source object.
    name_guid_map = {}
    for _ in tml_list:
        name_guid_map[_.content_name] = _.guid

    # Now for each edoc, create a TML object and then add FQNs to each table.
    for _ in tml_list:
        _.add_fqns_from_name_guid_map(name_guid_map=name_guid_map)


def _write_tml_obj_to_file(path: pathlib.Path, tml: TML) -> None:
    """
    Writes the TML to a file.
    :param path: The path to write to.  Can be a directory or filename.  If it's a directory, the file will be saved
    in the form <GUI>.<type>.TML
    :param TML:  The TML object to write to a file.
    :return: None
    """
    guid = tml.guid
    type = tml.content_type
    name = tml.content_name

    fn = f"{guid}.{type}.tml"
    if path:
        fn = f"{path}/{fn}"

    console.log(f'writing {name} to {fn}')
    tmlstr = YAMLTML.dump_tml_object(tml_obj=tml)
    with open(fn, "w") as f:
        f.write(tmlstr)


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


@app.command(name='import', cls=CSToolsCommand)
@depends(
    thoughtspot=common.setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
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
        connection: Optional[GUID] = O_(None,
                                        help="GUID for the target connection if tables need to be mapped to a new connection."),
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
):
    """
    Import TML from a file or directory into ThoughtSpot.
    """
    ts = ctx.obj.thoughtspot

    if not path.exists():
        console.stderr(f"[bold red]Error: {path} doesn't exist[/]")
        raise typer.Exit(-1)

    if import_policy == TMLImportPolicy.validate_only:
        console.log(f"[bold green]validating {path.name}.[/]")
    else:
        console.log(f"[bold green]importing {path.name} with policy {import_policy.value}.[/]")

    guid_mappings = _read_guid_mappings(guid_file=guid_file) if guid_file else {}

    tml: [TML] = []  # array of TML to update
    files = []
    if path.is_dir():
        for p in list(f for f in path.iterdir() if f.match("*.tml")):
            if not p.is_dir():  # don't currently support sub-folders.  Might add later.
                files.append(p)
                _load_and_append_tml_file(ts=ts, path=p, connection=connection, guid_mappings=guid_mappings,
                                          force_create=force_create, tml_list=tml)
    else:
        files.append(path)
        _load_and_append_tml_file(ts=ts, path=path, connection=connection, guid_mappings=guid_mappings,
                                  force_create=force_create, tml_list=tml)

    # remember the old guids in case we need to update the mapping.
    old_guids = [_.guid for _ in tml]

    # strip GUIDs if doing force create and convert to a list of TML string.
    if force_create:
        [_.remove_guid() for _ in tml]

    for f in files:
        console.log(f'{"validating" if import_policy == TMLImportPolicy.validate_only else "loading"} {f}')

    ok_resp = []  # responses for each item that didn't error.  Use for mapping and tagging.
    with console.status(f"[bold green]importing {path.name}[/]"):
        tml = [YAMLTML.dump_tml_object(_) for _ in tml]
        r = ts.api.metadata.tml_import(import_objects=tml,
                                       import_policy=import_policy.value,
                                       force_create=force_create)
        resp = _flatten_tml_response(r)
        fcnt = 0
        for _ in resp:
            if _.status_code == 'ERROR':
                console.log(f"[bold red]{files[fcnt]} {_.status_code}: {_.error_message} ({_.error_code})[/]")
            else:
                console.log(f"{files[fcnt]} {_.status_code}: {_.name} ({_.metadata_type}::{_.guid})")
                # if the object was loaded successfully and guid mappings are being used, make sure the mapping is there
                if guid_file:
                    guid_mappings[old_guids[fcnt]] = _.guid

            fcnt += 1
            ok_resp.append(_)

    if import_policy != TMLImportPolicy.validate_only:
        if guid_file:
            _write_guid_mappings(guid_file=guid_file, guid_mappings=guid_mappings)

        if tags:
            _add_tags(ts, ok_resp, tags)

        if share_with:
            _share_with(ts, ok_resp, share_with)


def _read_guid_mappings(guid_file: pathlib.Path) -> Dict:
    """
    Reads the guid mapping file and creates a dictionary of old -> new mappings.  Note that the GUID file _must_ be
    a valid TOML file of the format used by the scriptability tool.
    :param guid_file: The path to a file that may or may not exist.
    :return: A mapping of old to new GUIDs.
    """
    did_exist = _create_guid_file_if_not_exists(guid_file=guid_file)

    try:
        toml_content = toml.load(str(guid_file))
        mappings = toml_content.get('mappings', {})
        if not mappings:
            console.log(f"[bold yellow]Warning: No mappings provided in {guid_file}.[/]")

        return mappings

    except toml.decoder.TomlDecodeError as err:
        console.log(f"[bold red]Error reading the mapping file: {err}[/]")
        raise typer.Exit(-1)  # could also ignore, but would likely fail.


def _write_guid_mappings(guid_file: pathlib.Path, guid_mappings) -> None:
    """
    Writes the GUID mappings out to the mapping file.
    :param guid_file:
    :param guid_mappings:
    """
    _create_guid_file_if_not_exists(guid_file=guid_file)  # just to make sure.

    try:
        toml_content = toml.load(str(guid_file))
        toml_content["mappings"] = guid_mappings
        with open(guid_file, "w") as f:
            toml.dump(toml_content, f)

    except toml.decoder.TomlDecodeError as err:
        console.log(f"[bold red]Error writing to the mapping file: {err}[/]")
        raise typer.Exit(-1)  # could also ignore, but would likely fail.


def _create_guid_file_if_not_exists(guid_file: pathlib.Path) -> bool:
    """
    Creates a GUID file with a standard header if one doesn't exist.
    """
    if not guid_file.exists():
        mapping_header = ('# Automatically generated from cstools scriptability.'
                          'name="generated mapping file"'
                          'source="Source ThoughtSpot"'
                          'destination="Destination ThoughtSpot'
                          'description=""'
                          ''
                          '[mappings]'
                          f'version="{__version__}"'
                          )
        try:
            with guid_file.open(mode='w') as f:
                f.write(mapping_header)
        except Exception as e:
            console.log(f"[bold red]Unable to open file {guid_file}: {e}[/]")
            raise typer.Exit(-1)

        return False

    return True  # exists already


def _load_and_append_tml_file(
        ts: ThoughtSpot,
        path: pathlib.Path,
        connection: GUID,
        guid_mappings: Dict,
        force_create: bool,
        tml_list: List[TML]) -> GUID:
    """
    Loads a TML file from the path, getting table mappings if needed.  Then strip GUID if creating new.
    :param ts: The ThoughtSpot interface.
    :param path:  The file path.
    :param connection:  The connection to map to (optional).
    :param guid_mappings: The dictionary that maps from old GUID to new GUID.
    :param force_create: If true, files are being created.
    :param tml_list: A list that is being appended to.  Might get updated.
    :return: The old GUID or none if didn't get added
    """

    if path.is_dir():
        console.log(f"[bold red]Attempting to load a directory {path}.[/]")
        return None

    if not path.name.endswith(".tml"):
        console.log(f"[bold red]{path} Only TML (.tml) files are supported.[/]")
        return None

    tmlobj = _load_tml_from_file(ts=ts, path=path, connection=connection)

    old_guid = tmlobj.guid

    tml = _map_guids(tml=tmlobj, guid_mappings=guid_mappings)

    if tmlobj.content_type == TMLContentType.table.value:
        console.log(f"[bold red]Table import not currently selected.  Ignoring {path}.[/]")
    else:
        tml_list.append(tmlobj)

    return old_guid


def _load_tml_from_file(ts: ThoughtSpot, path: pathlib.Path, connection: GUID = None) -> TML:
    """
    Loads a TML object.  If it's a worksheet and the connection is provided, then the table FQNs will be modified.
    :param path: The path to the file.
    :param connection: The connection GUID (optional)
    :return: A TML object.
    """
    with open(path, "r") as tmlfile:
        tmlstr = tmlfile.read()

    tmlobj = YAMLTML.get_tml_object(tml_yaml_str=tmlstr)

    cnx = ts.connection if connection else None

    if tmlobj.content_type == TMLContentType.worksheet.value and connection:
        tmlobj = tmlobj
        console.log('map tables')

        tables = cnx.get_tables_for_connection(connection)
        table_map = {}  # name to FQN
        for _ in tables:
            table_map[_['name']] = _['id']
        tmlobj.remap_tables_to_new_fqn(name_to_fqn_map=table_map)

    return tmlobj


def _map_guids(tml: TML, guid_mappings: Dict) -> TML:
    """
    Updates the TML to map any known GUIDs to new GUIDs.  If the old GUID (guid in file) is in the mapping as a key,
    it will be replaced with the value.
    :param tml: A TML object to replace mappings on.
    :param guid_mappings: The mapping dictionary of the form guid_mapping[<old_guid>] => <new_guid>
    """

    # check all entries in the tml to see if they are GUID or FQN.
    # If yes, try to change the value.
    # If no, try mapping, but at the next level down.  Ruturn when there are no child levels.
    _find_and_map_guids(tml=tml.tml, guid_mappings=guid_mappings)
    return tml


def _find_and_map_guids(tml: Dict, guid_mappings: Dict) -> None:
    """
    Recursively finds GUIDs (guid or fqn entries) and replaces if the GUID is mapped.  This shouldn't get too deep.
    :param tml: The TML fragment to check.
    :param guid_mappings: The mapping to use.
    """
    guid_key_names = ('guid', 'fqn')
    for k in tml.keys():
        if k in guid_key_names:
            v = tml.get(k, None)
            if v and v in guid_mappings.keys():
                tml[k] = guid_mappings[v]
        elif isinstance(tml[k], dict):
            _find_and_map_guids(tml=tml[k], guid_mappings=guid_mappings)


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
                l = type_bundles.get(_.metadata_type, [])
                if not l:
                    type_bundles[_.metadata_type] = l
                l.append(_.guid)

            permissions = {}
            for g in groups:
                permissions[g] = AccessLevel.read_only

            for type in type_bundles.keys():
                objectids = type_bundles[type]
                ts.api.security.share(type=type, id=objectids, permissions=permissions)


@app.command(name='compare', cls=CSToolsCommand)
def compare(
        file1: pathlib.Path = A_(
            ...,
            help='full path to the first TML file to compare.',
            metavar='FILE1',
            dir_okay=False,
            resolve_path=True
        ),
        file2: pathlib.Path = A_(
            ...,
            help='full path to the second TML file to compare.',
            metavar='FILE2',
            dir_okay=False,
            resolve_path=True
        ),
):
    """
    Compares two TML files for differences.
    """

    tml1 = _get_tmlobj(file1)
    tml2 = _get_tmlobj(file2)

    with console.status(f"[bold green]Comparing {file1} and {file2}[/]"):
        same = _compare_tml(file1.name, tml1, file2.name, tml2)
        console.log(f"{file1} is{'' if same else ' not'} the same as {file2}")


def _get_tmlobj(path: pathlib.Path) -> TML:
    """Returns a TML object from the file path."""
    with open(path, "r") as tmlfile:
        tmlstr = tmlfile.read()

    return YAMLTML.get_tml_object(tml_yaml_str=tmlstr)


def _compare_tml(file1: str, tml1: TML, file2: str, tml2: TML) -> bool:
    """Compares two TML objects, listing any differences."""
    return __compare_dict(file1, tml1.tml, file2, tml2.tml)


def __compare_dict(f1: str, d1: dict, f2: str, d2: dict) -> bool:
    """Compares two dictionaries, logging any changes."""
    if not (type(d1) is dict and type(d2) is dict):
        console.log(f"[bold red]{d1} and {d2} are different types.")
        return False

    same = True

    # See if there are any keys in the first one that are not in the second.
    for k1 in d1.keys():
        if k1 not in d2.keys():
            console.log(f"[bold red]{k1} not in {f2}[/]")
            same = False

    # See if there are any keys in the second one that are not in the first.
    for k2 in d2.keys():
        if k2 not in d1.keys():
            console.log(f"[bold red]{k2} not in {f1}[/]")
            same = False

    # get the common keys
    common_keys = list(set(d1.keys()) & set(d2.keys()))

    for k in common_keys:
        if type(d1[k]) is dict:
            same = same and __compare_dict(f1, d1[k], f2, d2[k])  # need to set to false if one is false
        elif type(d1[k]) is list:
            same = same and __compare_list(f1, d1[k], f2, d2[k])  # need to set to false if one is false
        else:
            if d1[k] != d2[k]:
                console.log(f"[bold red]Values for key '{k}' are different: [/]")
                console.log(f"[bold red]]\t{d1[k]} != {d2[k]}[/]")
                same = False

    return same


def __compare_list(f1: str, l1: list, f2: str, l2: list) -> bool:
    """Compares the contents of a list."""
    same = True

    if not (type(l1) is list and type(l2) is list):
        console.log(f"[bold red]{l1} and {l2} are different types.")
        return False

    if len(l1) != len(l2):
        console.log(f"[bold red]]\t{l1} != {l2}[/]")
        same = False

    for cnt in range(0, len(l1)):
        if type(l1[cnt]) is dict:
            same = same and __compare_dict(f1, l1[cnt], f2, l2[cnt])
        elif type(l1[cnt]) is list:
            same = same and __compare_list(f1, l1[cnt], f2, l2[cnt])
        else:
            if l1[cnt] != l2[cnt]:
                console.log(f"[bold red]Values are different: [/]")
                console.log(f"[bold red]]\t{l1[cnt]} != {l2[cnt]}[/]")
                same = False


    return same






