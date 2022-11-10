from typing import List
import logging
import pathlib
import zipfile

import oyaml as yaml
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.sync.falcon import Falcon
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import console, CSToolsApp, CSToolsArgument as Arg, CSToolsOption as Opt
from cs_tools.const import FMT_TSLOAD_DATETIME
from cs_tools.util import to_datetime

from ._version import __version__


HERE = pathlib.Path(__file__).parent
log = logging.getLogger(__name__)


def _format_table_info_data(data: List[dict]) -> List[dict]:
    """
    Standardize data in an expected format.

    This is a simple transformation layer, we are fitting our data to be
    record-based and in the format that's expected for an eventual
    tsload command.
    """
    data = [
        {
            'database_name': e.get('database'),
            'schema_name': e.get('schema'),
            'table_name': e.get('name'),
            'table_guid': e['guid'],
            'state': e.get('state'),
            'database_version': e.get('databaseVersion'),
            'serving_version': e.get('servingVersion'),
            'building_version': e.get('buildingVersion'),
            'build_duration_s': e.get('buildDuration'),
            'is_known': e.get('isKnown'),
            'database_status': e.get('databaseStatus'),
            'last_uploaded_at': to_datetime(e.get('lastUploadedAt', 0), unit='us').strftime(FMT_TSLOAD_DATETIME),
            'num_of_rows': e.get('numOfRows'),
            'approx_bytes_size': e.get('approxByteSize'),
            'uncompressed_bytes_size': e.get('uncompressedByteSize'),
            'row_skew': e.get('rowSkew'),
            'num_shards': e.get('numShards'),
            'csv_size_with_replication_mb': e.get('csvSizeWithReplicationMB'),
            'replicated': e.get('replicated'),
            'ip': 'all' if e.get('ip') == -1 else e.get('ip', None)
        }
        for e in data['tables']
    ]
    return data


app = CSToolsApp(
    help="""
    Gather data on your existing Falcon tables for sharding.

    [b][yellow]USE AT YOUR OWN RISK![/b] This tool uses private API calls which
    could change on any version update and break the tool.[/]

    Once tables grow sufficiently large within a Falcon deployment, cluster
    performance and data loading can be enhanced through the use of sharding.
    The choice of what column to shards and how many shards to use can vary
    based on many factors. This tool helps expose that key information.

    Before sharding, it can be helpful to implement this solution and consult
    with your ThoughtSpot contact for guidance on the best shard key and number
    of shards to use.

    \b
    For further information on sharding, please refer to:
      https://docs.thoughtspot.com/latest/admin/loading/sharding.html
    """,
)


@app.command()
def spotapp(
    directory: pathlib.Path = Arg(
        ...,
        help='location on your machine to copy the SpotApp to',
        file_okay=False,
        resolve_path=True
    ),
    nodes: int = Opt(..., help='number of nodes serving your ThoughtSpot cluster'),
    cpu_per_node: int = Opt(56, help='number of CPUs serving each node'),
    threshold: int = Opt(
        55_000_000,
        help=(
            'unsharded row threshold, once exceeded a table will be a candidate for '
            'sharding'
        )
    ),
    ideal_rows: int = Opt(20_000_000, help='ideal rows per shard'),
    min_rows: int = Opt(15_000_000, help='minumum rows per shard'),
    max_rows: int = Opt(20_000_000, help='maximum rows per shard')
):
    """
    Exports the SpotApp associated with this tool.
    """
    parameters = {
        'parameter: CPU per Node': str(cpu_per_node),
        'parameter: Ideal Rows per Shard': str(ideal_rows),
        'parameter: Maximum Rows per Shard': str(max_rows),
        'parameter: Minimum Rows per Shard': str(min_rows),
        'parameter: Number of ThoughtSpot Nodes': str(nodes),
        'parameter: Unsharded Row Threshold': str(threshold)
    }
    tml = {}

    with zipfile.ZipFile(HERE / 'static' / 'spotapp_answer_v1.zip', mode='r') as z:
        for i, file in enumerate(z.infolist()):
            with z.open(file, 'r') as f:
                data = yaml.safe_load(f)

            data['guid'] = f'B07DFACE-F001-C0DE-ACED-BA5EBA11{i:04}'

            if file.filename == 'falcon_table_sharding.worksheet.tml':
                for formula in data['worksheet']['formulas']:

                    # process overrides
                    try:
                        formula['expr'] = parameters[formula['name']]
                    except KeyError:
                        pass

            tml[file] = data

    NAME = f'CS Tools Sharding Recommender SpotApp (v{__version__})'

    with zipfile.ZipFile(directory / f'{NAME}.zip', mode='w') as z:
        for file, content in tml.items():
            z.writestr(file, yaml.safe_dump(content))

    console.print(f'moved the [blue]{NAME}[/] to {directory}')


@app.command(dependencies=[thoughtspot])
def gather(
    ctx: typer.Context,
    export: str = Arg(
        ...,
        help='protocol and path for options to pass to the syncer',
        metavar='protocol://DEFINITION.toml',
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    )
):
    """
    Extract Falcon table info from your ThoughtSpot platform.
    """
    ts = ctx.obj.thoughtspot
    syncer = export if export is not None else Falcon()

    with console.status('[bold green]getting falcon table info'):
        data = _format_table_info_data(ts.api._periscope.sage_combinedtableinfo().json())

    if syncer.name == 'falcon':
        with console.status('[bold green]creating tables with remote TQL'):
            ts.tql.script(HERE / 'static' / 'create_tables.tql')
    elif hasattr(syncer, '__is_database__'):
        console.log(
            f'attempting to dump to database that is not Falcon! see the log file for '
            f'schema if the table FALCON_TABLE_INFO is not created in {syncer.name}.'
        )
        log.debug("""

            CREATE TABLE falcon_table_info (
                  database_name                 VARCHAR(255)
                , schema_name                   VARCHAR(255)
                , table_name                    VARCHAR(255)
                , table_guid                    VARCHAR(255)
                , state                         VARCHAR(255)
                , database_version              BIGINT
                , serving_version               BIGINT
                , building_version              BIGINT
                , build_duration_s              BIGINT
                , is_known                      BOOL
                , database_status               VARCHAR(255)
                , last_uploaded_at              DATETIME
                , num_of_rows                   BIGINT
                , approx_bytes_size             BIGINT
                , uncompressed_bytes_size       BIGINT
                , row_skew                      BIGINT
                , num_shards                    BIGINT
                , csv_size_with_replication_mb  DOUBLE
                , replicated                    BOOL
                , ip                            VARCHAR(255)
            );
        """)

    with console.status(f'[bold green]loading data to {syncer.name}..'):
        syncer.dump('falcon_table_info', data=data)
