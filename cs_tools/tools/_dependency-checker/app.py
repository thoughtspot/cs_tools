from typing import List, Dict
import pathlib
import shutil
import enum

from typer import Option as O_
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.util.datetime import to_datetime
from cs_tools.tools.common import to_csv, run_tql_script, tsload
from cs_tools.util.swagger import to_array
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


class ParentType(str, enum.Enum):
    """
    Limits the type of objects passed on via CLI.
    """
    SYSTEM_TABLE = 'system table'
    IMPORTED_DATA = 'imported data'
    WORKSHEET = 'worksheet'
    VIEW = 'view'


def _format_metadata_objects(metadata: List[Dict]):
    """
    Standardize data in an expected format.

    This is a simple transformation layer, we are fitting our data to be
    record-based and in the format that's expected for an eventual
    tsload command.
    """
    parents = []

    for parent in metadata:
        parents.append({
            'guid_': parent['id'],
            'name': parent['name'],
            'description': parent.get('description'),
            'author_guid': parent['author'],
            'author_name': parent['authorName'],
            'author_display_name': parent['authorDisplayName'],
            'created': to_datetime(parent['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
            'modified': to_datetime(parent['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
            # 'modified_by': parent['modifiedBy']  # user.guid
            'type': SystemType.to_friendly(parent['type'])
        })

    return parents


def _format_dependencies(dependencies: Dict[str, Dict]):
    """
    Standardize data in an expected format.

    This is a simple transformation layer, we are fitting our data to be
    record-based and in the format that's expected for an eventual
    tsload command.
    """
    children = []

    for parent_guid, dependencies_data in dependencies.items():
        for dependency_type, dependencies_ in dependencies_data.items():
            for dependency in dependencies_:
                children.append({
                    'guid_': dependency['id'],
                    'parent_guid': parent_guid,
                    'name': dependency['name'],
                    'description': dependency.get('description'),
                    'author_guid': dependency['author'],
                    'author_name': dependency['authorName'],
                    'author_display_name': dependency['authorDisplayName'],
                    'created': to_datetime(dependency['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                    'modified': to_datetime(dependency['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                    # 'modified_by': dependency['modifiedBy']  # user.guid
                    'type': SystemType.to_friendly(dependency.get('type', dependency_type))
                })

    return children


def _get_dependents(api: ThoughtSpot, parent: str, metadata: List[Dict]) -> List[Dict]:
    guids = to_array([item['id'] for item in metadata])
    r = api._dependency.list_dependents(type='LOGICAL_TABLE', id=guids, batchsize=-1)
    return r.json()


def _get_recordset_metadata(api: ThoughtSpot) -> Dict[str, List]:
    r = api._metadata.list(type='LOGICAL_TABLE', batchsize=-1).json()['headers']

    metadata = {
        'system table': [],
        'imported data': [],
        'worksheet': [],
        'view': [],
        'other': []
    }

    for item in r:
        try:
            friendly = SystemType.to_friendly(item['type'])
        except AttributeError:
            friendly = 'other'

        metadata[friendly].append(item)

    return metadata


app = typer.Typer(
    help="""
    Make Dependencies searchable in your platform.

    [b][yellow]USE AT YOUR OWN RISK![/b] This tool uses private API calls which
    could change on any version update and break the tool.[/]

    Dependencies can be collected for various types of metadata. For example,
    many tables are used within a worksheet, while many worksheets will have
    answers and pinboards built on top of them.

    \b
    Metadata Object             Metadata Dependent
    - guid                      - guid
    - name                      - parent guid
    - description               - name
    - author guid               - description
    - author name               - author guid
    - author display name       - author name
    - created                   - author display name
    - modified                  - created
    - object type               - modified
                                - object type

    \f
    Also available, but not developed for..

    Table Column        -> LOGICAL_COLUMN
    Tag / Stickers      -> TAG
    Embrace Connections -> DATA_SOURCE
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
      - introspect_metadata_dependent
    """
    for file in (HERE / 'static').glob('*.tml'):
        shutil.copy(file, save_path)


@app.command(cls=RichCommand)
@frontend
def gather(
    save_path: pathlib.Path=O_(None, help='if specified, directory to save data to'),
    parent: ParentType=O_(None, help='type of object to find dependents for'),
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

    if parent is None:
        parents = [e.value for e in ParentType]
    else:
        parents = [parent]

    with ThoughtSpot(cfg) as api:
        metadata   = _get_recordset_metadata(api)

        for parent in parents:
            dependents = _get_dependents(api, parent, metadata[parent])
            parents  = _format_metadata_objects(metadata[parent])
            children = _format_dependencies(dependents)

            fp = dir_ / 'introspect_metadata_object.csv'
            mode, header = ('a', False) if fp.exists() else ('w', True)
            to_csv(parents, fp, mode=mode, header=header)

            if children:
                fp = dir_ / 'introspect_metadata_dependent.csv'
                mode, header = ('a', False) if fp.exists() else ('w', True)
                to_csv(children, fp, mode=mode, header=header)

        if save_path is not None:
            return

        run_tql_script(api, fp=HERE / 'static' / 'create_tables.tql')

        for stem in ('introspect_metadata_object', 'introspect_metadata_dependent'):
            path = dir_ / f'{stem}.csv'
            cycle_id = tsload(api, fp=path, target_database='cs_tools', target_table=stem)
            path.unlink()

            if cycle_id is None:
                continue

            r = api.ts_dataservice.load_status(cycle_id).json()
            m = api.ts_dataservice._parse_tsload_status(r)
            console.print(m)
