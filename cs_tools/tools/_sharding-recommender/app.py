from typing import List
import pathlib
import shutil

from typer import Option as O_
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.util.datetime import to_datetime
from cs_tools.tools.common import run_tql_command, run_tql_script, tsload
from cs_tools.settings import TSConfig
from cs_tools.const import FMT_TSLOAD_DATETIME
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.tools import common


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
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def spotapp(
    export: pathlib.Path = O_(None, help='directory to save the spot app to', file_okay=False, resolve_path=True),
    **frontend_kw
):
    """
    Exports the SpotApp associated with this tool.
    """
    shutil.copy(HERE / 'static' / 'spotapps.zip', export)
    console.print(f'moved the SpotApp to {export}')


@app.command(cls=RichCommand)
@frontend
def gather(
    export: pathlib.Path = O_(None, help='directory to save the spot app to', file_okay=False, resolve_path=True),
    # maintained for backwards compatability
    backwards_compat: pathlib.Path = O_(None, '--save_path', help='backwards-compat if specified, directory to save data to', hidden=True),
    **frontend_kw
):
    """
    Gather and optionally, insert data into Falcon.

    By default, data is automatically gathered and inserted into the
    platform. If save_path argument is used, data will not be inserted
    and will instead be dumped to the location specified.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    dir_ = cfg.temp_dir if export is None else export
    dir_.parent.mkdir(exist_ok=True)
    path = dir_ / 'falcon_table_info.csv'

    with ThoughtSpot(cfg) as ts:
        with console.status('getting Falcon table info'):
            data = _format_table_info_data(ts.api._periscope.sage_combinedtableinfo().json())

        with console.status('saving Falcon table info'):
            common.to_csv(data, fp=path, mode='a')
            console.print(f'wrote {len(data): >7,} rows to {path}')

        if export is not None:
            return

        with console.status('creating tables with remote TQL'):
            run_tql_command(ts, command='CREATE DATABASE cs_tools;')
            run_tql_script(ts, fp=HERE / 'static' / 'create_tables.tql')

        with console.status('loading data to Falcon with remote tsload'):
            cycle_id = tsload(
                ts,
                fp=path,
                target_database='cs_tools',
                target_table='falcon_table_info',
                has_header_row=True
            )
            path.unlink()
            r = ts.api.ts_dataservice.load_status(cycle_id).json()
            m = ts.api.ts_dataservice._parse_tsload_status(r)
            console.print(m)
