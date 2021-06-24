from typing import List, Dict
import pathlib
import shutil
import enum

from typer import Option as O_
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.util.datetime import to_datetime
from cs_tools.tools.common import to_csv, run_tql_script, tsload
from cs_tools.settings import TSConfig
from cs_tools.const import FMT_TSLOAD_DATETIME
from cs_tools.api import ThoughtSpot


HERE = pathlib.Path(__file__).parent


class SystemType(str, enum.Enum):
    """
    Reversible mapping of system to friendly names.
    """
    ONE_TO_ONE_LOGICAL = 'system table'
    USER_DEFINED = 'imported data'
    WORKSHEET = 'worksheet'
    AGGR_WORKSHEET = 'view'
    PINBOARD_ANSWER_BOOK = 'pinboard'
    QUESTION_ANSWER_BOOK = 'saved answer'

    @classmethod
    def to_friendly(cls, value) -> str:
        return getattr(cls, value).value

    @classmethod
    def to_system(cls, value) -> str:
        return getattr(cls, value).name

    @classmethod
    def to_metadata_type(cls, value) -> str:
        e = cls(value)

        if 'BOOK' in e.name:
            return e.name
        return 'LOGICAL_TABLE'


def _format_metadata_objects(metadata: List[Dict], type_: str):
    """
    Standardize data in an expected format.

    This is a simple transformation layer, we are fitting our data to be
    record-based and in the format that's expected for an eventual
    tsload command.
    """
    objects = []

    for meta in metadata:
        objects.append({
            'guid_': meta['id'],
            'name': meta['name'],
            'description': meta.get('description'),
            'author_guid': meta['author'],
            'author_name': meta['authorName'],
            'author_display_name': meta['authorDisplayName'],
            'created': to_datetime(meta['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
            'modified': to_datetime(meta['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
            # 'modified_by': meta['modifiedBy']  # user.guid
            'type': SystemType.to_friendly(meta['type']) if meta.get('type') else type_
        })

    return objects


app = typer.Typer(
    help="""
    Make ThoughtSpot content searchable in your platform.

    [b][yellow]USE AT YOUR OWN RISK![/b] This tool uses private API calls which
    could change on any version update and break the tool.[/]

    Metadata is created through normal ThoughtSpot activities. Tables, Worksheets,
    Answers, and Pinboards are all examples of metadata.

    \b
    Metadata Object
    - guid
    - name
    - description
    - author guid
    - author name
    - author display name
    - created
    - modified
    - object type
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def tml(
    save_path: pathlib.Path=O_(..., help='filepath to save TML files to', prompt=True),
    **frontend_kw
):
    """
    Create TML files.

    Generates and saves multiple TML files.

    \b
    TABLE:
      - introspect_metadata_object
    """
    for file in (HERE / 'static').glob('*.tml'):
        shutil.copy(file, save_path)


@app.command(cls=RichCommand)
@frontend
def gather(
    save_path: pathlib.Path=O_(None, help='if specified, directory to save data to'),
    metadata: SystemType=O_(None, help='type of object to find data for'),
    **frontend_kw
):
    """
    Gather and optionally, insert data into Falcon.

    By default, data is automatically gathered and inserted into the
    platform. If save_path argument is used, data will not be inserted
    and will instead be dumped to the location specified.
    """
    app_dir = pathlib.Path(typer.get_app_dir('cs_tools'))
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    if save_path is not None and (not save_path.exists() or save_path.is_file()):
        console.print(f'[red]"{save_path.resolve()}" should be a valid directory![/]')
        raise typer.Exit()

    dir_ = save_path if save_path is not None else app_dir

    if metadata is not None:
        metadata_types = [metadata]
    else:
        metadata_types = list(SystemType)

    with ThoughtSpot(cfg) as api:
        with console.status('getting top level metadata'):
            for metadata in metadata_types:
                type_ = SystemType.to_metadata_type(metadata.value)
                r = api._metadata.list(type=type_, batchsize=-1).json()['headers']
                objects = _format_metadata_objects(r, metadata.value)

                # if we're only looking for a LOGICAL_TABLE subtype..
                # system table, imported data, worksheet, view
                if type_ == 'LOGICAL_TABLE':
                    objects = list(filter(lambda e: e['type'] == metadata.value, objects))

                fp = dir_ / 'introspect_metadata_object.csv'
                mode, header = ('a', False) if fp.exists() else ('w', True)
                to_csv(objects, fp, mode=mode, header=header)

        if save_path is not None:
            return

        run_tql_script(api, fp=HERE / 'static' / 'create_tables.tql')

        path = dir_ / 'introspect_metadata_object.csv'
        cycle_id = tsload(api, fp=path, target_database='cs_tools', target_table='introspect_metadata_object')
        path.unlink()

        r = api.ts_dataservice.load_status(cycle_id).json()
        m = api.ts_dataservice._parse_tsload_status(r)
        console.print(m)
