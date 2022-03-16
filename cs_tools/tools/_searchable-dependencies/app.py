from typing import List, Dict
import pathlib
import shutil
import enum

from typer import Option as O_
import typer

from cs_tools.helpers.cli_ux import console, frontend, CSToolsGroup, CSToolsCommand
from cs_tools.util.datetime import to_datetime
from cs_tools.tools.common import run_tql_command, run_tql_script, tsload
from cs_tools.util.algo import chunks
from cs_tools.settings import TSConfig
from cs_tools.const import FMT_TSLOAD_DATETIME
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.tools import common

from .util import FileQueue


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
    MATERIALIZED_VIEW = 'materialized view'
    CALENDAR_TABLE = 'custom calendar'
    FORMULA = 'formula'

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


def _format_metadata_objects(queue, metadata: List[Dict]):
    """
    Standardize data in an expected format.

    This is a simple transformation layer, we are fitting our data to be
    record-based and in the format that's expected for an eventual
    tsload command.
    """
    for parent in metadata:
        queue.put({
            'guid_': parent['id'],
            'name': parent['name'],
            'description': parent.get('description'),
            'author_guid': parent['author'],
            'author_name': parent['authorName'],
            'author_display_name': parent['authorDisplayName'],
            'created': to_datetime(parent['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
            'modified': to_datetime(parent['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
            # 'modified_by': parent['modifiedBy']  # user.guid
            'type': SystemType.to_friendly(parent['type']) if parent.get('type') else 'column',
            'context': parent.get('owner')
        })


def _format_dependency(queue, parent_guid, dependencies: Dict[str, Dict]):
    """
    Standardize data in an expected format.

    This is a simple transformation layer, we are fitting our data to be
    record-based and in the format that's expected for an eventual
    tsload command.
    """
    for dependency in dependencies:
        queue.put({
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
            'type': SystemType.to_friendly(dependency['type'])
        })


def _get_dependents(api: ThoughtSpot, queue, parent: str, metadata: List[Dict]):
    for chunk in chunks(metadata, n=50):
        r = api._dependency.list_dependents(
                id=[_['id'] for _ in chunk],
                type='LOGICAL_COLUMN' if parent in ('formula', 'column') else 'LOGICAL_TABLE',
                batchsize=-1,
                timeout=None if parent == 'column' else 0
            )

        for parent_guid, dependent_data in r.json().items():
            for dependency_type, dependencies in dependent_data.items():
                for dependency in dependencies:
                    dependency['type'] = dependency.get('type', dependency_type)

                    queue.put({
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
                        'type': SystemType.to_friendly(dependency['type'])
                    })


def _get_recordset_metadata(api: ThoughtSpot) -> Dict[str, List]:
    _seen = {}
    metadata = {
        'system table': [],
        'imported data': [],
        'worksheet': [],
        'view': [],
        'formula': [],
        'column': [],
        'other': []
    }

    active_users = common.batched(
        api._metadata.list,
        type='USER',
        batchsize=5000,
        transformer=lambda r: r.json()['headers']
    )

    r = [
        *common.batched(
            api._metadata.list,
            type='LOGICAL_TABLE',
            batchsize=5000,
            transformer=lambda r: r.json()['headers']
        ),
        *common.batched(
            api._metadata.list,
            type='LOGICAL_COLUMN',
            batchsize=5000,
            # NOTE: "True" = includes Custom Calendars & Materialized Views...
            # auto_created=False,
            transformer=lambda r: r.json()['headers']
        )
    ]

    for item in r:
        try:
            friendly = SystemType.to_friendly(item['type'])
        except KeyError:
            friendly = 'column'
        except AttributeError:
            friendly = 'other'

        author = next((u for u in active_users if u['id'] == item['author']), None) or {}
        parent = _seen.get(item['owner']) or {}

        item = {
            **item,
            'friendly': friendly,
            'owner': parent.get('name'),
            'authorName': author.get('name') or item.get('authorName'),
            'authorDisplayName': author.get('displayName') or item.get('authorDisplayName'),
        }

        _seen[item['id']] = item
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
    - context                   - object type

    \f
    Also available, but not developed for..

    Tag / Stickers      -> TAG
    Embrace Connections -> DATA_SOURCE
    """,
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
@frontend
def spotapp(
    export: pathlib.Path = O_(None, help='directory to save the spot app to', file_okay=False, resolve_path=True),
    # maintained for backwards compatability
    backwards_compat: pathlib.Path = O_(None, '--save_path', help='backwards-compat if specified, directory to save data to', hidden=True),
    **frontend_kw
):
    """
    Exports the SpotApp associated with this tool.
    """
    shutil.copy(HERE / 'static' / 'spotapps.zip', export)
    console.print(f'moved the SpotApp to {export}')


@app.command(cls=CSToolsCommand)
@frontend
def gather(
    export: pathlib.Path = O_(None, help='directory to save the spot app to', file_okay=False, resolve_path=True),
    parent: ParentType=O_(None, help='type of object to find dependents for'),
    include_columns: bool=O_(False, '--include-columns', help='whether or not to find column dependents', show_default=False),
    # hidden options
    http_timeout: int=O_(5.0, '--timeout', help='TQL network call timeout threshold'),
    # maintained for backwards compatability
    backwards_compat: pathlib.Path = O_(None, '--save_path', help='backwards-compat if specified, directory to save data to', hidden=True),
    **frontend_kw
):
    """
    Gather and optionally, insert data into Falcon.

    By default, data is automatically gathered and inserted into the
    platform. If --export argument is used, data will not be inserted
    and will instead be dumped to the location specified.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)
    export = export or backwards_compat

    dir_ = cfg.temp_dir if export is None else export
    dir_.parent.mkdir(exist_ok=True)

    static = HERE / 'static'
    parent_types = [e.value for e in ParentType] if parent is None else [parent]

    if include_columns:
        parent_types.extend(['formula', 'column'])

    with ThoughtSpot(cfg) as ts:
        with console.status('getting top level metadata'):
            metadata = _get_recordset_metadata(ts.api)

        parent_q = FileQueue(dir_ / 'introspect_metadata_object.csv')
        children_q = FileQueue(dir_ / 'introspect_metadata_dependent.csv')

        with parent_q as pq, children_q as cq:
            for parent in parent_types:
                with console.status(f'getting dependents of metadata: {parent}'):
                    _format_metadata_objects(pq, metadata[parent])
                    _get_dependents(ts.api, cq, parent, metadata[parent])

        if export is not None:
            return

        try:
            with console.status('creating tables with remote TQL'):
                run_tql_command(ts, command='CREATE DATABASE cs_tools;', http_timeout=http_timeout)
                run_tql_script(ts, fp=static / 'create_tables.tql', raise_errors=True, http_timeout=http_timeout)
        except common.TableAlreadyExists:
            with console.status('altering tables with remote TQL'):
                run_tql_script(ts, fp=static / 'alter_tables.tql', http_timeout=http_timeout)

        with console.status('loading data to Falcon with remote tsload'):
            for stem in ('introspect_metadata_object', 'introspect_metadata_dependent'):
                path = dir_ / f'{stem}.csv'
                cycle_id = tsload(
                    ts,
                    fp=path,
                    target_database='cs_tools',
                    target_table=stem,
                    has_header_row=True
                )
                path.unlink()
                r = ts.api.ts_dataservice.load_status(cycle_id).json()
                m = ts.api.ts_dataservice._parse_tsload_status(r)
                console.print(m)