import logging
import pathlib
import zipfile

import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import console, CSToolsApp, CSToolsArgument as Arg, CSToolsOption as Opt

from ._version import __version__
from .models import FalconTableInfo
import _ext_api


HERE = pathlib.Path(__file__).parent
log = logging.getLogger(__name__)


app = CSToolsApp(
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
)


# @app.command()
# def deploy_spotapp(
#     connection_guid: str = Arg(),
#     nodes: int = Opt(..., help='number of nodes serving your ThoughtSpot cluster'),
#     cpu_per_node: int = Opt(56, help='number of CPUs serving each node'),
#     threshold: int = Opt(
#         55_000_000,
#         help='unsharded row threshold, once exceeded a table will be a candidate for sharding'
#     ),
#     ideal_rows: int = Opt(20_000_000, help='ideal rows per shard'),
#     min_rows: int = Opt(15_000_000, help='minumum rows per shard'),
#     max_rows: int = Opt(20_000_000, help='maximum rows per shard')
# ):
#     """
#     Deploy the Sharding Recommender SpotApp.
#     """


# @app.command()
# def spotapp(
#     directory: pathlib.Path = Arg(
#         ...,
#         help='location on your machine to copy the SpotApp to',
#         file_okay=False,
#         resolve_path=True
#     ),
#     nodes: int = Opt(..., help='number of nodes serving your ThoughtSpot cluster'),
#     cpu_per_node: int = Opt(56, help='number of CPUs serving each node'),
#     threshold: int = Opt(
#         55_000_000,
#         help=(
#             'unsharded row threshold, once exceeded a table will be a candidate for '
#             'sharding'
#         )
#     ),
#     ideal_rows: int = Opt(20_000_000, help='ideal rows per shard'),
#     min_rows: int = Opt(15_000_000, help='minumum rows per shard'),
#     max_rows: int = Opt(20_000_000, help='maximum rows per shard')
# ):
#     """
#     Exports the SpotApp associated with this tool.
#     """
#     parameters = {
#         'parameter: CPU per Node': str(cpu_per_node),
#         'parameter: Ideal Rows per Shard': str(ideal_rows),
#         'parameter: Maximum Rows per Shard': str(max_rows),
#         'parameter: Minimum Rows per Shard': str(min_rows),
#         'parameter: Number of ThoughtSpot Nodes': str(nodes),
#         'parameter: Unsharded Row Threshold': str(threshold)
#     }
#     tml = {}

#     with zipfile.ZipFile(HERE / 'static' / 'spotapp_answer_v1.zip', mode='r') as z:
#         for i, file in enumerate(z.infolist()):
#             with z.open(file, 'r') as f:
#                 data = yaml.safe_load(f)

#             data['guid'] = f'B07DFACE-F001-C0DE-ACED-BA5EBA11{i:04}'

#             if file.filename == 'falcon_table_sharding.worksheet.tml':
#                 for formula in data['worksheet']['formulas']:

#                     # process overrides
#                     try:
#                         formula['expr'] = parameters[formula['name']]
#                     except KeyError:
#                         pass

#             tml[file] = data

#     NAME = f'CS Tools Sharding Recommender SpotApp (v{__version__})'

#     with zipfile.ZipFile(directory / f'{NAME}.zip', mode='w') as z:
#         for file, content in tml.items():
#             z.writestr(file, yaml.safe_dump(content))

#     console.print(f'moved the [blue]{NAME}[/] to {directory}')


@app.command(dependencies=[thoughtspot])
def gather(
    ctx: typer.Context,
    syncer: str = Arg(
        ...,
        help="protocol and path for options to pass to the syncer",
        metavar="protocol://DEFINITION.toml",
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx, models=[FalconTableInfo]),
    ),
):
    """
    Extract Falcon table info from your ThoughtSpot platform.
    """
    ts = ctx.obj.thoughtspot

    with console.status("[bold green]getting falcon table info"):
        r = _ext_api.periscope_sage_combined_table_info(ts.api)

        if not r.success:
            console.log(f"[red]could not get falcon table info {r}")
            raise typer.Exit(1)

        data = [FalconTableInfo.from_api_v1(_) for _ in r.json()["tables"]]

    with console.status(f"[bold green]loading data to {syncer.name}.."):
        syncer.dump("ts_falcon_table_info", data=data)
