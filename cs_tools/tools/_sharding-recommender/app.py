from typing import List
import pathlib
import shutil

from typer import Option as O_
import typer

from cs_tools.helpers.cli_ux import console, show_tool_options, frontend
from cs_tools.util.datetime import to_datetime
from cs_tools.tools.common import to_csv, run_tql_script, tsload
from cs_tools.settings import TSConfig
from cs_tools.const import FMT_TSLOAD_DATETIME
from cs_tools.api import ThoughtSpot


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
    callback=show_tool_options,
    invoke_without_command=True
)


@app.command()
@frontend
def generate_tml(
    save_path: pathlib.Path=O_(..., help='filepath to save TML files to', prompt=True),
    **frontend_kw
):
    """
    Create TML files.

    Generates and saves multiple TML files.

    \b
    TABLE ...... falcon_table_info
    WORKSHEET .. PS: Falcon Table Sharding Recommender
    PINBOARD ...
    """
    # TODO: enforce parameters???

    # TODO: use TML apis
    # end user shouldn't need to worry about this doesn't need to worry about this step)

    # TODO: check TS version
    # mostly because of feature parity in TML between 6.0, 6.2, 6.3, 7.0, 7.0.1
    worksheet_tml = 'Table Sharding Recommender.worksheet.tsl'
    pinboard_tml  = 'Falcon Table Shard Analysis.pinboard.tsl'

    for stem in (table_tml, pinboard_tml):
        shutil.copy(HERE / 'static' / stem, save_path)


@app.command()
@frontend
def gather(
    save_path: pathlib.Path=O_(None, help='if specified, directory to save data to'),
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

    dir_ = save_path if save_path is not None else app_dir
    fp = dir_ / 'falcon_table_info.csv'

    with ThoughtSpot(cfg) as api:
        data = _format_table_info_data(api._periscope.sage_combinedtableinfo().json())
        to_csv(data, fp=fp)

        if save_path is not None:
            return

        # TODO .. should we do a version check?
        # rTQL released in 6.2.1+
        # rTSLOAD released in 6.3+
        run_tql_script(api, fp=HERE / 'static' / 'create_tables.tql')
        cycle_id = tsload(api, fp=fp, target_database='cs_tools', target_table='falcon_table_info')
        (dir_ / 'falcon_table_info.csv').unlink()

        r = api.ts_dataservice.load_status(cycle_id)
        data = r.json()

        console.print(
            f'Cycle ID: {data["cycle_id"]}'
            f'\nStage: {data["internal_stage"]}'
            f'\nRows written: {data["rows_written"]}'
            f'\nIgnored rows: {data["ignored_row_count"]}'
        )
