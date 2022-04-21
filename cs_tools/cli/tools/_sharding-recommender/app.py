from typing import List
import pathlib
import shutil

from typer import Option as O_
import typer

from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT
from cs_tools.sync.falcon import Falcon
from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand, SyncerProtocolType
from cs_tools.util import to_datetime
from cs_tools.const import FMT_TSLOAD_DATETIME
from cs_tools.cli.tools import common


HERE = pathlib.Path(__file__).parent


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


app = typer.Typer(
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
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
def spotapp(
    export: pathlib.Path = O_(None, help='directory to save the spot app to', file_okay=False, resolve_path=True)
):
    """
    Exports the SpotApp associated with this tool.
    """
    shutil.copy(HERE / 'static' / 'spotapps.zip', export)
    console.print(f'moved the SpotApp to {export}')


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=common.setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def gather(
    ctx: typer.Context,
    export: str = O_(
        None,
        help='protocol and path for options to pass to the syncer',
        metavar='protocol://DEFINITION.toml',
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    )
):
    """
    Gather and optionally, insert data into Falcon.

    By default, data is automatically gathered and inserted into the
    platform. If --export argument is used, data will not be inserted
    and will instead be dumped to the location specified.
    """
    ts = ctx.obj.thoughtspot
    syncer = export if export is not None else Falcon()

    with console.status('[bold green]getting falcon table info'):
        data = _format_table_info_data(ts.api._periscope.sage_combinedtableinfo().json())

    if isinstance(syncer, Falcon):
        with console.status('[bold green]creating tables with remote TQL'):
            ts.tql.script(HERE / 'static' / 'create_tables.tql')

    with console.status(f'[bold green]loading data to {syncer.name}..'):
        syncer.dump('falcon_table_info', data=data)
