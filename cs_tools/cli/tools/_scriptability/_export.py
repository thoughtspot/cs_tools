"""
This file contains the methods to execute the 'scriptability export' command.
"""
import pathlib
from typing import List

import click
import typer
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
        raise CSToolsError(error=f"{path} is not a directory.",
                           reason=f"Only directories are supported for export.",
                           mitigation="Rerun with a directory to export to.")

    ts = ctx.obj.thoughtspot
    export_ids = strip_blanks(export_ids)
    tags = strip_blanks(tags)

    # Scenarios to support
    # GUID/tags only - download the content and save
    # With associated - download content with associated and save
    # With fqns - download content with associated, map FQNs, save content specified (original or with FQNs)

    if tags:
        export_ids.extend(ts.metadata.get_object_ids_with_tags(tags))

    for guid in export_ids:
        with console.status((f"[bold green]exporting {guid} {'with' if export_associated else 'without'}"
                             f"associated content.[/]")):

            r = ts.api.metadata.tml_export(export_ids=[guid],  # only doing one at a time to account for FQN mapping
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
            for _ in filter(lambda tml: export_associated or tml.guid == guid, tml_objects):
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
