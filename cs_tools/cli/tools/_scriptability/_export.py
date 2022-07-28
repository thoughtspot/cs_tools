"""
This file contains the methods to execute the 'scriptability export' command.
"""
import click
import pathlib
from httpx import HTTPStatusError
from typing import List, Tuple

from rich.table import Table
from thoughtspot_tml import YAMLTML
from thoughtspot_tml.tml import TML
from typer import Argument as A_, Option as O_

from cs_tools.cli.types import CommaSeparatedValuesType
from cs_tools.cli.ux import console
from cs_tools.errors import CSToolsError
from cs_tools.data.enums import TMLType
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
        owner: str = O_('', metavar='USERNAME',
                        help='username that owns the content to download'),
        export_associated: bool = O_(False,
                                     help='if specified, also export related content'),
        set_fqns: bool = O_(False,
                            help='if set, then the content in the TML will have FQNs (GUIDs) added.')
):
    """
    Exports TML as YAML from ThoughtSpot.  There are three different parameters that can impact content to download:
    - tags: only content with these tags will be downloaded.
    - owner: only content owned by this owner will be downloaded.
    - GUIDs: only content with the specific GUIDs will be downloaded.

    At least one needs to be specified.  If you specify GUIDs then you can't use tags or owner.  Only the objects for
    the specific GUIDs.  Using GUIDs with tags or owner will give an error.
    If you don't specify GUIDs, then you must specify a tag and/or owner.  If you specify both, only items with the
    owner AND tag will be downloaded. For example, if you export for the "finance" tag and owner "user123", then
    only content owned by that user with the "finance" tag will be exported.
    """
    if export_ids and (tags or owner):
        raise CSToolsError(error="GUID and owner/tag specified.",
                           reason="You can only specify GUIDs or an owner or tag.",
                           mitigation="Modify you parameters to have GUIDS or owner/tag.  "
                                      "Note that tags and owner can be used together.")

    if not path.is_dir():
        raise CSToolsError(error=f"{path} is not a directory.",
                           reason=f"Only directories are supported for export.",
                           mitigation="Rerun with a valid directory to export to.")

    ts = ctx.obj.thoughtspot

    # do some basic cleanup to make sure we don't have extra spaces.
    export_ids = strip_blanks(export_ids)
    tags = strip_blanks(tags)
    owner = owner.strip() if owner else None

    # Scenarios to support
    # GUID/tags/owners - download the content and save
    # With associated - download content with associated and save
    # With fqns - download content with associated, map FQNs, save content specified (original or with FQNs)

    # GUIDs vs. tags/owner have already been accounted for so this should only happen if GUIDs were not specified.
    if tags or owner:
        owner_guid = ts.user.get_guid(owner) if owner else None
        export_ids.extend(ts.metadata.get_object_ids_with_tags_or_owner(tags=tags, owner=owner_guid))

    results = []  # (guid, status, name)
    for guid in export_ids:
        with console.status((f"[bold green]exporting {guid} {'with' if export_associated else 'without'}"
                             f"associated content.[/]")):

            try:
                r = ts.api.metadata.tml_export(export_ids=[guid],  # only doing one at a time to account for FQN mapping
                                               formattype=TMLType.yaml.value,  # formattype=formattype
                                               export_associated=(export_associated or set_fqns))

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
                        console.log(f"{_['info']['filename']} (OK)")
                        tmlobj = YAMLTML.get_tml_object(tml_yaml_str=_['edoc'])
                        tml_objects.append(tmlobj)
                        results.append((guid, status['status_code'], _['info']['name'], ""))

                if set_fqns:
                    # getting associated, this will also get the additional FQNs for the objects and add to the TML.
                    _add_fqns_to_tml(tml_list=tml_objects)

                # if the export_associated was specified, write all, else just write the requested.
                for _ in filter(lambda tml: export_associated or tml.guid == guid, tml_objects):
                    _write_tml_obj_to_file(path=path, tml=_)

            except HTTPStatusError as e:
                # Sometimes getting 400 errors on the content.  Need to just log an error and continue.
                console.log(f'Error exporting TML for GUID {guid}: {e}')
                results.append((guid, 'HTTP ERROR', 'UNK', f"{e}"))

    _show_results_as_table(results=results)


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
    :param tml:  The TML object to write to a file.
    :return: None
    """
    guid = tml.guid
    ctype = tml.content_type
    name = tml.content_name

    fn = f"{guid}.{ctype}.tml"
    if path:
        fn = f"{path}/{fn}"

    console.log(f'writing {name} to {fn}')
    tmlstr = YAMLTML.dump_tml_object(tml_obj=tml)
    with open(fn, "w") as f:
        f.write(tmlstr)


def _show_results_as_table(results: List[Tuple]) -> None:
    """
    Writes a pretty results table to the console.
    :param results: A list with the results of the load.  The values are (guid, status, name, desc) in that order.
    """
    table = Table(title="Import Results")

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
