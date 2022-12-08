"""
This file contains the methods to execute the 'scriptability export' command.
"""
import click
import pathlib
from httpx import HTTPStatusError
from typing import Any, Dict, List, Tuple, Union
from rich.table import Table
from typer import Argument as A_, Option as O_

from thoughtspot_tml.utils import determine_tml_type
from thoughtspot_tml.types import TMLObject
from thoughtspot_tml.exceptions import TMLDecodeError

from cs_tools.cli.types import CommaSeparatedValuesType
from cs_tools.cli.ux import console
from cs_tools.errors import CSToolsError
from cs_tools.data.enums import DownloadableContent, GUID, MetadataObjectSubtype, TMLType
from .util import strip_blanks


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
                                   help='comma separated list of GUIDs to export'),
        author: str = O_('', metavar='USERNAME',
                         help='username that is the author of the content to download'),
        pattern: str = O_(None, metavar='PATTERN',
                          help="Pattern for name with % as a wildcard"),
        include_types: List[str] = O_([], metavar='CONTENTTYPES',
                                      callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
                                      help='list of types to include: answer, liveboard, view, sqlview, '
                                           'table, connection'),
        exclude_types: List[str] = O_([], metavar='CONTENTTYPES',
                                      callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
                                      help='list of types to exclude (overrides include): answer, liveboard, view, '
                                           'sqlview, table, connection'),
        export_associated: bool = O_(False,
                                     help='if specified, also export related content'),
        set_fqns: bool = O_(False,
                            help='if set, then the content in the TML will have FQNs (GUIDs) added.'),
        org: str = O_(None, help='Name of org to export from.  The user must have access to that org.')
):
    """
    Exports TML as YAML from ThoughtSpot.  There are different parameters that can impact content to download:
    - GUIDs: only content with the specific GUIDs will be downloaded.
    - filters, e.g tags, author, pattern, include_types, exclude_types.

    At least one needs to be specified.  If you specify GUIDs then you can't use any filters.  Only the objects for
    the specific GUIDs.  Using GUIDs with filters will give an error.

    If you specify multiple filters, only items that match all filters will be downloaded. For example, if you export
    for the "finance" tag and author "user123", then only content owned by that user with the "finance" tag will be
    exported.
    """

    if export_ids and (tags or author or include_types or exclude_types or pattern):
        raise CSToolsError(error="GUID cannot be used with other filters.",
                           reason="You can only specify GUIDs or a combination of other filters, " 
                                  "such as author and tag.",
                           mitigation="Modify you parameters to have GUIDS or author/tag.  "
                                      "Note that tags and author can be used together.")

    if not path.is_dir():
        raise CSToolsError(error=f"{path} is not a directory.",
                           reason=f"Only directories are supported for export.",
                           mitigation="Rerun with a valid directory to export to.")

    ts = ctx.obj.thoughtspot

    # As-of 11/30/22 - we can't support pre8.7.  Functionality needs to be added to the thoughtspot_tml library.
    # do recent code version stuff
    platform_main, platform_secondary, *other = ts.platform.version.split('.')
    if int(platform_main) < 8 or (int(platform_main) == 8 and int(platform_secondary) < 7):
        raise NotImplementedError('Only ThoughtSpot 8.7+ is currently supported')

    # if an org was passed, switch context to that org.
    if org:
        ts.api.session.orgs_put(ts.org.lookup_id_for_name(org_name=org))

    # Scenarios to support
    # GUID/filters - download the content and save
    # With associated - download content with associated and save
    # With fqns - download content with associated, map FQNs, save content specified (original or with FQNs)

    # do some basic cleanup to make sure we don't have extra spaces or case issues.
    export_ids = strip_blanks(export_ids)
    tags = strip_blanks(tags)
    include_types = [_.strip().lower() for _ in include_types]
    exclude_types = [_.strip().lower() for _ in exclude_types]
    author = author.strip() if author else None

    # [
    #     {"id": "<GUID>", "type": DownloadableContent, "subtype": MetadataObjectSubtype | None},
    #     {"id": "<GUID>", "type": DownloadableContent, "subtype": MetadataObjectSubtype | None},
    # ]
    export_objects: List[Dict[str, Any]] = []

    # GUIDs vs. filters have already been accounted for so this should only happen if GUIDs were not specified.
    if export_ids:
        export_objects = ts.metadata.get_object_types(export_ids)
    else:
        author_guid = ts.user.get_guid(author) if author else None

        # convert  types to downloadable content types
        include_types = _convert_types_to_downloadable_content(include_types)
        exclude_types = _convert_types_to_downloadable_content(exclude_types)

        export_objects = (ts.metadata.get_object_ids_filtered(tags=tags,
                                                              author=author_guid,
                                                              pattern=pattern,
                                                              include_types=include_types,
                                                              exclude_types=exclude_types))

    results: List[Tuple[GUID, str, str, str]] = []  # (guid, status, name, message)
    for obj in export_objects:
        guid = obj['id']
        metadata_type = obj['type']
        with console.status((f"[bold green]exporting {guid} ({metadata_type}) {'with' if export_associated else 'without'}"
                             f"associated content.[/]")):

            try:
                if metadata_type == DownloadableContent.data_source:
                    results.extend(_download_connection(ts=ts, path=path, guid=guid))
                else:  # everything except connections.
                    results.extend(_download_tml(ts=ts, path=path, guid=guid,
                                                 export_associated=export_associated, set_fqns=set_fqns))

            except HTTPStatusError as e:
                # Sometimes getting 400 errors on the content.  Need to just log an error and continue.
                console.log(f'Error exporting TML for GUID {guid}: {e}.  Check for access permissions.')
                results.append((guid, 'HTTP ERROR', 'UNK', f"{e}"))

    _show_results_as_table(results=results)


def _download_connection(ts,
                         path: pathlib.Path,
                         guid: GUID,
                         ) -> List[Tuple[GUID, str, str, str]]:
    """Download a connection.  Connections aren't supported by TML yet."""
    results: List[Tuple[GUID, str, str, str]] = []  # (guid, status, name, message)

    r = ts.api._connection.export(guid)

    fn = f"{path}/{guid}.connection.tml"
    yaml = r.content.decode()
    name = yaml.split('\n')[0].split(": ")[1]

    try:
        with open(fn, "w") as yamlfile:
            yamlfile.write(yaml)
        results.append((guid, 'OK', name, 'Success'))
    except IOError as e:
        results.append((guid, 'ERROR', name, f'Error writing to file {fn}'))

    return results


def _download_tml(ts,
                  path: pathlib.Path,
                  guid: GUID,
                  export_associated: bool,
                  set_fqns: bool
                  ) -> List[Tuple[GUID, str, str, str]]:
    results: List[Tuple[GUID, str, str, str]] = []  # (guid, status, name, message)

    # 8.7.+ had export_fqn.  For previous versions we need to always get associated.  After we don't unless specified.
    r = ts.api.metadata.tml_export(export_ids=[guid],  # only doing one at a time to account for FQN mapping
                                   formattype=TMLType.yaml.value,  # formattype=formattype
                                   # export_associated=(export_associated or set_fqns),  # pre-8.7
                                   export_associated=export_associated,
                                   export_fqn=True)

    objects = r.json().get('object', [])

    tml_objects = []
    for _ in objects:
        status = _['info']['status']
        if not status['status_code'] == 'OK':  # usually access errors.
            console.log(f"[bold red]unable to get {_['info']['name']}: {_['info']['status']}[/]")
            results.append((guid,
                            status['status_code'],
                            _['info']['name'],
                            f"{_['info']['status']['error_message']}"))

        else:
            console.log(f"{_['info']['filename']} (Downloaded)")
            try:
                tml_type = determine_tml_type(info=_["info"])
                tmlobj = tml_type.loads(tml_document=_["edoc"])
                # tmlobj = YAMLTML.get_tml_object(tml_yaml_str=_['edoc'])

                tml_objects.append(tmlobj)
                results.append((guid, status['status_code'], _['info']['name'], "Success"))
            except TMLDecodeError as tde:  # some objects might not be supported
                console.log(f"[bold red]Unable to convert {_['edoc']} to a TML object.  Ignoring. {tde}")
                results.append((guid, 'WARNING', _['info']['name'], "Unable to convert to TML object"))

    # pre-8.7 needs to be added back when we add support.
    # if set_fqns:
        # getting associated, this will also get the additional FQNs for the objects and add to the TML.
    #     _add_fqns_to_tml(tml_list=tml_objects)

    # if the export_associated was specified, write all, else just write the requested.
    for _ in filter(lambda tml: export_associated or tml.guid == guid, tml_objects):
        _write_tml_obj_to_file(path=path, tml=_)

    return results


def _add_fqns_to_tml(tml_list: List[TMLObject]) -> None:
    """
    Looks up and adds the FQNs to the TML content.
    :param tml_list: List of TML types.
    """

    # First map all the names to GUIDs.  Names should be unique if starting with a single source object.
    name_guid_map = {}
    for _ in tml_list:
        name_guid_map[_.name] = _.guid

    # Now for each edoc, create a TML object and then add FQNs to each table.
    for _ in tml_list:
        _.add_fqns_from_name_guid_map(name_guid_map=name_guid_map)


def _write_tml_obj_to_file(path: pathlib.Path, tml: TMLObject) -> None:
    """
    Writes the TML to a file.
    :param path: The path to write to.  Can be a directory or filename.  If it's a directory, the file will be saved
    in the form <GUI>.<type>.TML
    :param tml:  The TML object to write to a file.
    :return: None
    """
    fn = path.name if not path.is_dir() else f"{path}/{tml.guid}.{tml.tml_type_name}.tml"

    console.log(f'writing {tml.name} to {fn}')
    tml.dump(fn)


def _show_results_as_table(results: List[Tuple]) -> None:
    """
    Writes a pretty results table to the console.
    :param results: A list with the results of the load.  The values are (guid, status, name, desc) in that order.
    """
    table = Table(title="Export Results")

    table.add_column("Status", no_wrap=True)
    table.add_column("GUID", no_wrap=True)
    table.add_column("Name", no_wrap=True)
    table.add_column("Desc", no_wrap=False)

    table._min_width = {"Status": 3}

    results.sort(key=lambda x: x[1])  # sort by the status
    for v in results:
        # table.add_row(v[0], v[1], v[2], v[3])
        # trimming to try to get all columns to show
        table.add_row(v[1][:8], v[0][:20], v[2][:20], v[3][:30])

    console.print(table)


def _convert_types_to_downloadable_content(types: List[str]) \
        -> List[Tuple[DownloadableContent, Union[MetadataObjectSubtype, None]]]:
    """
    Converts types, such as 'liveboard' to downloadable content types, such as DownloadableContent.pinboard
    :param types: A list of names of types.  Current types can be: answer, liveboard, view, sqlview, table, connection
    :return:  A list of tuples of (DownloadableContent, MetadataObjectSubtype).  Subtypes only apply to logical tables.
    :exception CSToolsError:  Thrown if there is an unknown type.
    """
    type_map = {
        "answer": DownloadableContent.saved_answer,
        "connection": DownloadableContent.data_source,
        "liveboard": DownloadableContent.pinboard,
        "sqlview": DownloadableContent.logical_table,  # subtype is "SQL_VIEW"
        "table": DownloadableContent.logical_table, # subtype is "ONE_TO_ONE_LOGICAL"
        "view": DownloadableContent.logical_table,  # subtype is "AGGR_WORKSHEET"
        "worksheet": DownloadableContent.logical_table,  # subtype is "WORKSHEET"
    }

    subtype_map = {
        "answer": None,
        "connection": None,
        "liveboard": None,
        "sqlview": MetadataObjectSubtype.sql_view,  # subtype is "SQL_VIEW"
        "table": MetadataObjectSubtype.system_table, # subtype is "ONE_TO_ONE_LOGICAL"
        "view": MetadataObjectSubtype.view,  # subtype is "AGGR_WORKSHEET":w
        "worksheet": MetadataObjectSubtype.worksheet,  # subtype is "WORKSHEET"
    }

    download_types = []
    for t in types:
        if t not in type_map.keys():
            raise CSToolsError(error=f'Unknown type: {t}',
                               reason=f'You must specify only valid types.',
                               mitigation=f'try again with one of the valid types: '
                                          f'[{",".join(list(type_map.keys()))}]')
        dt = type_map.get(t)
        dst = subtype_map.get(t)

        download_types.append((dt, dst))

    return download_types
