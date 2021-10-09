from typing import List
import pathlib
import shutil

from typer import Option as O_
import typer
import yaml

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
def tml(
    save_path: pathlib.Path=O_(..., help='directory to save TML files to', prompt=True),
    nodes: int=O_(4, help='number of nodes in your ThoughtSpot cluster', prompt=True),
    cpus_per_node: int=O_(56, help='number of CPUs per node in your cluster', prompt=True),
    **frontend_kw
):
    """
    Create TML files.

    Generates and saves multiple TML files.

    \b
    TABLE:
      - falcon_table_info

    \b
    WORKSHEET:
      - PS: Falcon Table Sharding Recommender

    \b
    PINBOARD:
      - PS: Falcon Table Sharding Recommender
    """
    with (HERE / 'static' / 'PS_ Falcon Table Sharding.worksheet.tml').open() as in_:
        data = yaml.full_load(in_)

        # set the parameters
        for formula in data['worksheet']['formulas']:
            if formula['name'] == '❔ CPU per Node':
                formula['expr'] = f'{cpus_per_node}'  # constant formulas in TS are str

            if formula['name'] == '❔ Total ThoughtSpot Nodes':
                formula['expr'] = f'{nodes}'  # constant formulas in TS are str

        with (save_path / 'PS_ Falcon Table Sharding.worksheet.tml').open('w') as out:
            yaml.dump(data, out)

    # TODO: use TML apis
    # end user shouldn't need to worry about this doesn't need to worry about this step)

    # TODO: check TS version
    # mostly because of feature parity in TML between 6.0, 6.2, 6.3, 7.0, 7.0.1
    table_tml = 'falcon_table_info.table.tml'
    pinboard_tml  = 'PS_ Falcon Table Sharding Analysis.pinboard.tml'

    for stem in (table_tml, pinboard_tml):
        shutil.copy(HERE / 'static' / stem, save_path)


@app.command(cls=RichCommand)
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
    common.check_exists(save_path)

    dir_ = save_path if save_path is not None else app_dir
    path = dir_ / 'falcon_table_info.csv'

    with ThoughtSpot(cfg) as ts:
        with console.status('getting Falcon table info'):
            data = _format_table_info_data(ts.api._periscope.sage_combinedtableinfo().json())

        common.to_csv(data, fp=path, mode='a')

        if save_path is not None:
            return

        with console.status('creating tables with remote TQL'):
            run_tql_command(ts, command='CREATE DATABASE cs_tools;')
            run_tql_script(ts, fp=HERE / 'static' / 'create_tables.tql')

        with console.status('loading data to Falcon with remote tsload'):
            cycle_id = tsload(
                ts,
                fp=path,
                target_database='cs_tools',
                target_table='falcon_table_info'
            )
            path.unlink()
            r = ts.api.ts_dataservice.load_status(cycle_id).json()
            m = ts.api.ts_dataservice._parse_tsload_status(r)
            console.print(m)
