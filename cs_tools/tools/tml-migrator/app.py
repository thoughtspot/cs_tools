# DEV NOTE:
#


import json
import pathlib
from typer import Argument as A_, Option as O_  # noqa
import typer
from typing import List

from cs_tools._enums import TMLType
from cs_tools.helpers.cli_ux import _csv, console, CSToolsCommand, CSToolsGroup, frontend
from cs_tools.settings import TSConfig
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.tools import common

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
        export_ids: List[str] = A_(..., metavar='GUIDS',
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

    export_ids = [xid for xid in export_ids if xid]  # strip out blank values.

    console.log(f"[bold green]extracting {export_ids} as {format_type.value} " +
                f"{'with ' if export_associated else 'without '} associated.[/]")

    with ThoughtSpot(cfg) as ts:
        with console.status(f"[bold green]extracting....[/]"):
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
