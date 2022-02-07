# DEV NOTE:
#

import pathlib

import yaml
from typer import Argument as A_, Option as O_  # noqa
import typer
from typing import List

from cs_tools._enums import TMLImportPolicy, TMLType
from cs_tools.helpers.cli_ux import _csv, console, CSToolsCommand, CSToolsGroup, frontend
from cs_tools.settings import TSConfig
from cs_tools.thoughtspot import ThoughtSpot


def strip_blanks(list: List[str]) -> List[str]:
    return [l for l in list if l]


app = typer.Typer(
    help="""
    Tool for easily migrating TML between clusters.

    ThoughtSpot provides the ability to extract object metadata (tables, worksheets, liveboards, etc.) 
    in ThoughtSpot Modeling Language (TML) format, which is a text format based on YAML.  These files 
    can be modified and uploaded into another instance. These files can then be modified and imported 
    into another (or the same) instance to either create or modify objects.

      cs_tools tools tml-migration --help
    
    \f
    TODO - add more details on using the tools and a workflow.
    
    DEV NOTE:

      Two control characters are offered in order to help with
      docstrings in typer App helptext and command helptext
      (docstrings).

      \b - Preserve Whitespace / formatting.
      \f - EOF, don't include anything after this character in helptext.
    """,
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
@frontend
def export(
        tags: List[str] = O_([], metavar='TAGS',
                             callback=_csv,
                             help='list of tags to export for'),
        export_ids: List[str] = O_([], metavar='GUIDS',
                                    callback=_csv,
                                    help='list of guids to export'),
        format_type: TMLType = O_(TMLType.yaml.value,
                                  help=f'if specified, format to export, either {TMLType.yaml.value} or {TMLType.json.value}'),
        export_associated: bool = O_(False,
                                     help='if specified, also export related content'),
        path: pathlib.Path = O_(  # may not want to use
            None,
            help='full path (directory) to save data set to',
            metavar='DIR',
            dir_okay=True,
            resolve_path=True
        ),
        **frontend_kw
) -> None:
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    export_ids = strip_blanks(export_ids)
    tags = strip_blanks(tags)

    console.log(f"[bold green]exporting {export_ids} as {format_type.value} " +
                f"{'with ' if export_associated else 'without '} associated.[/]")

    with ThoughtSpot(cfg) as ts:
        if tags:
            export_ids.extend(_get_object_ids_with_tags(ts,tags))

        with console.status(f"[bold green]exporting....[/]"):
            r = ts.api.metadata.tml_export(export_ids=export_ids,
                                           format_type=format_type,
                                           export_associated=export_associated)
            objects = r.json()['object']
            for _ in objects:
                status = _['info']['status']
                if not status['status_code'] == 'OK':  # usually access errors.
                    console.log(f"unable to get {_['info']['name']}: {_['info']['status']}")

                else:
                    fn = _['info'].get('filename', None)
                    if path:
                        fn = f"{path}/{fn}"

                    console.log(f'\twriting {fn}')
                    with open (fn, "w") as f:
                        f.write(_['edoc'])

    return None


def _get_object_ids_with_tags(ts, tags: List[str]) -> List[str]:
    object_ids = []

    # TODO Verify if these are all the types.  It seems to be the ones we want other than connections.
    types = (
        'QUESTION_ANSWER_BOOK',
        'PINBOARD_ANSWER_BOOK',
        'LOGICAL_TABLE',
        'DATA_SOURCE'
    )

    console.log(f"Getting GUIDs for tag {tags}")

    for metadata_type in types:
        offset = 0

        while True:
            r = ts.api._metadata.list(type=metadata_type, batchsize=500, offset=offset, tagname=tags)
            data = r.json()
            offset += len(data)

            for metadata in data['headers']:
                console.log(f"{metadata['id']}: {metadata['name']} -- {metadata['description']}")
                object_ids.append(metadata["id"])

            if data['isLastBatch']:
                break

    console.log(object_ids)
    return list(set(object_ids))


@app.command(cls=CSToolsCommand)
@frontend
def upload(  # can't use import, since that's a reserved word.
        path: pathlib.Path = A_(
            ...,
            help='full path to the TML file(s) to upload.  Could be .zip',
            metavar='FILE',
            dir_okay=False,
            resolve_path=True
        ),
        import_policy: TMLImportPolicy = O_(TMLImportPolicy.validate_only.value,
                                            help="The import policy type"),
        force_create: bool = O_(True,
                                help="If true, will force a new object to be created."),
        **frontend_kw
) -> None:
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    if not path.exists():
        console.log(f"[bold red]Error: {path} doesn't exist[/]")
        exit(-1)

    if import_policy == TMLImportPolicy.validate_only:
        console.log(f"[bold green]validating {path.name}.[/]")
    else:
        console.log(f"[bold green]importing {path.name} with policy {import_policy.value}.[/]")

    tml = yaml.load(path.read_text("utf-8"), Loader=yaml.Loader)

    with ThoughtSpot(cfg) as ts:
        with console.status(f"[bold green]importing {path.name}[/]"):
            r = ts.api.metadata.tml_import(import_objects=tml,
                                           import_policy=import_policy.value,
                                           force_create=force_create)
            console.log(f"{r.status_code}: {r.text}")

    return None
