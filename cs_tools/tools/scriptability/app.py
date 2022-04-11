# DEV NOTE:
#
# Future enhancements:
#   - add tags on upload
#   - ability to manipulate objects, such as renaming references to worksheets and tables, token replacement, etc.
#

import datetime
import json
import pathlib
import requests
from thoughtspot_tml import *
from thoughtspot_tml.tml import TML
from typer import Argument as A_, Option as O_  # noqa
from typing import Dict, List
import typer
import yaml
from zipfile import ZipFile

from cs_tools import util
from cs_tools._enums import GUID, TMLImportPolicy, TMLType, TMLContentType
from cs_tools.middlewares import ConnectionMiddleware
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

      cs_tools tools scriptability-migration --help
    
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
        # TODO - consider JSON format in the future.  Not currently needed.
        # format_type: TMLType = O_(TMLType.yaml.value,
        #                  help=f'if specified, format to export, either {TMLType.yaml.value} or {TMLType.json.value}'),
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
    if not path.is_dir():
        console.stderr(f"[bold red]Only directories are supported for export.  {path} is not a directory.[/]")

    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    export_ids = strip_blanks(export_ids)
    tags = strip_blanks(tags)

    # Options:
    #    guids, no associated
    #    guids, associated
    #    tag, associated
    #    tag, not associated
    # if associated - get all the guids, then get the mapping of types, then call to use edoc
    # if not associated - get all the guids, then call export

    with ThoughtSpot(cfg) as ts:
        if tags:
            export_ids.extend(ts.metadata.get_object_ids_with_tags(tags))

        if not export_associated:
            with console.status(f"[bold green]exporting ${export_ids} without associated content.[/]"):
                r = ts.api.metadata.tml_export(export_ids=export_ids,
                                               format_type=TMLType.yaml.value,  # format_type=format_type
                                               export_associated=export_associated)

                # TODO - add code to check that I got something back and handle errors.
                objects = r.json().get('object', [])
                for _ in objects:
                    status = _['info']['status']
                    if not status['status_code'] == 'OK':  # usually access errors.
                        console.log(f"[bold red]unable to get {_['info']['name']}: {_['info']['status']}[/]")

                    else:
                        console.log(f"{_['info']['filename']} (OK)")
                        _write_tml_obj_to_file(path=path, tml=_)

        else:  # getting associated, so get the full pack.
            with console.status(f"[bold green]exporting ${export_ids} with associated content.[/]"):
                object_list = ts.metadata.get_edoc_object_list(export_ids)
                r = ts.api._metadata.edoc_export_epack(
                    {
                        "object": object_list,
                        "export_dependencies": True
                    }
                )
                console.log(r)
                _write_tml_package_to_file(path=path, contents=r.json()['zip_file'])

    return None


def _write_tml_obj_to_file(path: pathlib.Path, tml: str) -> None:
    """
    Writes the TML to a file.
    :param path: The path to write to.  Can be a directory or filename.  If it's a directory, the file will be saved
    in the form <GUI>.<type>.TML
    :param TML:  The TML as a JSON object returned from ThoughtSpot
    :return: None
    """
    guid = tml['info']['id']
    type = tml['info']['type']
    name = tml['info']['name']

    fn = f"{guid}.{type}.tml"
    if path:
        fn = f"{path}/{fn}"

    console.log(f'writing {name} to {fn}')
    with open (fn, "w") as f:
        f.write(tml['edoc'])


def _write_tml_package_to_file(path: pathlib.Path, contents: str) -> None:
    """
    :param path: The path to write to.  Can be a directory or filename.  If it's a directory, the file will be saved
    in the form <GUI>.<type>.TML
    :param contents: The contents to write to the zip file.
    :return: None
    """
    now = datetime.datetime.now().strftime("_%Y%m%d_%H%M%S")
    filepath = path / f"{now}.scriptability.zip"
    util.base64_to_file(contents, filepath=filepath)

    try:
        with ZipFile(filepath, 'r') as zippy:
            for info in zippy.infolist():
                with zippy.open(info.filename) as tml_file:
                    if (info.filename.endswith('tml')):
                        (filename, tml_type, _) = info.filename.split('.', maxsplit=3)
                        console.log(f'writing {filename}')
                        tml_obj = YAMLTML.get_tml_object(tml_file.read().decode('utf-8'))
                        tml_outfile = path / f"{tml_obj.guid}.{tml_obj.content_type}.tml"
                        with open(tml_outfile, 'w') as outfile:
                            outfile.write(YAMLTML.dump_tml_object(tml_obj))
    except Exception as err:
        console.stderr(f"[bold red]{err}[/]")


@app.command(cls=CSToolsCommand)
@frontend
def upload(  # can't use import, since that's a reserved word.
        path: pathlib.Path = A_(
            ...,
            help='full path to the TML file or directory to upload.',
            metavar='FILE_OR_DIR',
            dir_okay=True,
            resolve_path=True
        ),
        import_policy: TMLImportPolicy = O_(TMLImportPolicy.validate_only.value,
                                            help="The import policy type"),
        force_create: bool = O_(False,
                                help="If true, will force a new object to be created."),
        connection: str = O_(None,
                             help="GUID for the target connection if tables need to be mapped to a new connection."),
        **frontend_kw
) -> None:
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)
    connection = GUID(connection)

    if not path.exists():
        console.stderr(f"[bold red]Error: {path} doesn't exist[/]")
        exit(-1)

    if import_policy == TMLImportPolicy.validate_only:
        console.log(f"[bold green]validating {path.name}.[/]")
    else:
        console.log(f"[bold green]importing {path.name} with policy {import_policy.value}.[/]")

    tml = []  # array of TML to update

    with ThoughtSpot(cfg) as ts:

        files = []
        if path.is_dir():
            file_list = list(f for f in path.iterdir() if f.match("*.tml"))
            for f in file_list:
                console.log(f'{"validating" if import_policy == TMLImportPolicy.validate_only else "loading"} {f}')

            for p in file_list:
                if not p.is_dir():  # don't currently support sub-folders.  Might add later.
                    tmlobj = _load_tml_from_file(ts=ts, path=p, connection=connection)
                    if tmlobj.content_type == TMLContentType.table.value:
                        console.log(f"[bold red]Table import not currently supported.  Ignoring {p}.[/]")
                    else:
                        files.append(p.name)
                        tml.append(tmlobj.tml)
        else:
            # TODO - consider supporting .zip files in the future by extracting the files.
            # TODO - currently tables aren't supported.
            if not path.name.endswith(".tml"):
                console.log(f"[bold red]Only TML files are currently supported.[/]")
            else:
                tmlobj = _load_tml_from_file(ts=ts, path=path, connection=connection)
                if tmlobj.content_type == TMLContentType.table:
                    console.log(f"[bold red]Table import not currently selected.  Ignoring file.[/]")
                else:
                    tml.append(tmlobj.tml)

        with console.status(f"[bold green]importing {path.name}[/]"):
            r = ts.api.metadata.tml_import(import_objects=tml,
                                           import_policy=import_policy.value,
                                           force_create=force_create)
            resp = _flatten_tml_response(r)
            fcnt = 0
            for _ in resp:
                if _['status_code'] == 'ERROR':
                    console.log(f"[bold red]{files[fcnt]} {_['status_code']}: {_['error_message']} ({_['error_code']})[/]")
                else:
                    console.log(f"{files[fcnt]} {_['status_code']}: {_['name']} ({_['type']}::{_['guid']})")
                fcnt += 1

    return None


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

    cnx = ConnectionMiddleware(ts) if connection else None

    if tmlobj.content_type == TMLContentType.worksheet.value and connection:
        tmlobj = tmlobj
        console.log('map tables')

        tables = cnx.get_tables_for_connection(connection)
        table_map = {}  # name to FQN
        for _ in tables:
            table_map[_['name']] = _['id']
        tmlobj.remap_tables_to_new_fqn(name_to_fqn_map=table_map)

    return tmlobj


def _flatten_tml_response(r: Dict) -> [Dict]:
    """
    Flattens a response to return key fields as an array of dictionaries for easier use.
    :param r: The response as a JSON object.
    :return: An array of individual responses objects.
      Keys for success are: status_code, guid, name, type, metadata_type
      Keys for error are: status_code, error_code, error_message
    """
    flat = []

    text = json.loads(r.text)
    for _ in text['object']:
        resp = {'status_code': _['response']['status']['status_code']}
        if resp['status_code'] == 'OK':
            h = _['response']['header']
            resp['guid'] = h.get('id_guid', 'UNKNOWN')
            resp['name'] = h.get('name', 'UNKNOWN')
            resp['type'] = h.get('type', 'UNKNOWN')
            resp['metadata_type'] = h.get('metadata_type', 'UNKNOWN')
        else:
            resp['error_code'] = _['response']['status']['error_code']
            resp['error_message'] = _['response']['status']['error_message'].replace('<br/>', '')

        flat.append(resp)

    return flat


def raise_tml_errors(response: requests.Response) -> Dict:
    if len(response.content) == 0:
        raise Exception(f'No response returned at all with status code {response.status_code}')
    else:
        j = response.json()
        # JSON error response checking
        if 'object' in j:
            for k in j['object']:
                if 'info' in k:
                    # Older versions wrapped the errors in 'info'
                    if k['info']['status']['status_code'] == 'ERROR':
                        # print(k['info']['status']['error_message'])
                        raise SyntaxError(k['info']['status']['error_message'])
                    else:
                        return response.json()
                # Recent versions return as 'response'
                elif 'response' in k:
                    if k['response']['status']['status_code'] == 'ERROR':
                        # print(k['info']['status']['error_message'])
                        raise SyntaxError(k['response']['status']['error_message'])
                    else:
                        return response.json()
                else:
                    return response.json()

        else:
            return response.json()

