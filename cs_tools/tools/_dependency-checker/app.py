from typing import Any, List, Dict
import pathlib
import shutil
import enum

from typer import Option as O_
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.util.datetime import to_datetime
from cs_tools.tools.common import run_tql_command, run_tql_script, tsload
from cs_tools.util.swagger import to_array
from cs_tools.util.algo import chunks
from cs_tools.settings import TSConfig
from cs_tools.const import FMT_TSLOAD_DATETIME
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.tools import common


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
            'type': SystemType.to_friendly(parent['type']) if parent.get('type') else 'column',
            'context': parent.get('owner')
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

    for parent_guid, dependencies_ in dependencies.items():
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
                'type': SystemType.to_friendly(dependency['type'])
            })

    return children


def _get_dependents(api: ThoughtSpot, parent: str, metadata: List[Dict]) -> List[Dict[str, Any]]:
    # DEV NOTE: (@boonhapus)
    #
    # I don't like magic numbers. Why am I using chunks=50? Why are we using
    # batchsize=5000? Well, because we have no clear guidelines on how much data can be
    # passed back and forth to the API. For even moderately sized clusters, column
    # dependents could be in the hundreds of thousands. Consider a few worksheets with
    # 60 columns each, shared with 50 users, who then create 10 answers (or worse,
    # pinboards) each - all referencing a popular underlying physical column, like a
    # measure.
    #
    # 1 column * 3 worksheets * 50 users * 10 answers = 53 dependencies logged .. for a single column
    #
    # This adds up fast. This a toy scenario. ThoughtSpot response output just doesn't
    # like that. So we're being conservative and asking for 50 guids' dependencies at a
    # time. Then we're also batching the output so that we get only 5000 dependencies in
    # each response.
    #
    # We can normalize across the chunks and batches in RAM, later.
    data = {}

    # normalize and flatten the dependency batch data.
    #
    # r = [
    #     {
    #         'guid1': {
    #             'LOGICAL_TABLE': [{}, ...],         # dependency headers
    #             'PINBOARD_ANSWER_BOOK': [{}, ...],  # dependency headers
    #             ...
    #         },
    #         'guid2': { ... },
    #         ...
    #     },
    #     {
    #         'guid5001': {},
    #         'guid5002': {},
    #         ...
    #     }
    # ]
    for chunk in chunks(metadata, n=50):
        r = common.batched(
                api._dependency.list_dependents,
                type='LOGICAL_COLUMN' if parent in ('formula', 'column') else 'LOGICAL_TABLE',
                id=[item['id'] for item in chunk],
                batchsize=5000,
                transformer=lambda r: [r.json()]
            )

        for batch in r:
            for guid, dependent_data in batch.items():
                for dependent_type, dependencies in dependent_data.items():
                    if guid not in data:
                        data[guid] = []

                    for dependency in dependencies:
                        dependency['type'] = dependency.get('type', dependent_type)
                        data[guid].append(dependency)

    return data


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
    include_columns: bool=O_(False, '--include-columns', help='whether or not to find column dependents', show_default=False),
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
    common.check_exists(save_path)

    dir_ = save_path if save_path is not None else app_dir
    static = HERE / 'static'
    parent_types = [e.value for e in ParentType] if parent is None else [parent]

    if include_columns:
        parent_types.extend(['formula', 'column'])

    with ThoughtSpot(cfg) as ts:
        with console.status('getting top level metadata'):
            metadata = _get_recordset_metadata(ts.api)

        for parent in parent_types:
            with console.status(f'getting dependents of metadata: {parent}'):
                dependents = _get_dependents(ts.api, parent, metadata[parent])
                parents = _format_metadata_objects(metadata[parent])
                children = _format_dependencies(dependents)

            if not parents:
                continue

            with console.status(f'saving metadata: {parent}'):
                path = dir_ / 'introspect_metadata_object.csv'
                common.to_csv(parents, path, mode='a')

                if not children:
                    continue

            with console.status(f'saving children metadata: {parent}'):
                path = dir_ / 'introspect_metadata_dependent.csv'
                common.to_csv(children, path, mode='a')

        if save_path is not None:
            return

        try:
            with console.status('creating tables with remote TQL'):
                run_tql_command(ts, command='CREATE DATABASE cs_tools;')
                run_tql_script(ts, fp=static / 'create_tables.tql', raise_errors=True)
        except common.TableAlreadyExists:
            with console.status('altering tables with remote TQL'):
                run_tql_script(ts, fp=static / 'alter_tables.tql')

        with console.status('loading data to Falcon with remote tsload'):
            for stem in ('introspect_metadata_object', 'introspect_metadata_dependent'):
                path = dir_ / f'{stem}.csv'
                cycle_id = tsload(
                    ts,
                    fp=path,
                    target_database='cs_tools',
                    target_table=stem
                )
                path.unlink()
                r = ts.api.ts_dataservice.load_status(cycle_id).json()
                m = ts.api.ts_dataservice._parse_tsload_status(r)
                console.print(m)
