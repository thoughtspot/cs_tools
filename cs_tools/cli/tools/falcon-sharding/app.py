import pathlib
import logging

from thoughtspot_tml.utils import determine_tml_type
from thoughtspot_tml import Table, Worksheet
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import rich_console
from cs_tools.cli.ux import CSToolsArgument as Arg
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import CSToolsApp
from cs_tools.types import TMLImportPolicy

from .models import FalconTableInfo
from . import _extended_rest_api_v1

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


@app.command(dependencies=[thoughtspot])
def deploy(
    ctx: typer.Context,
    falcon_database: str = Opt("cs_tools", help="name of the database where data is gathered to"),
    nodes: int = Opt(..., help='number of nodes serving your ThoughtSpot cluster'),
    cpu_per_node: int = Opt(56, help='number of CPUs serving each node'),
    threshold: int = Opt(
        55_000_000,
        help='unsharded row threshold, once exceeded a table will be a candidate for sharding'
    ),
    ideal_rows: int = Opt(20_000_000, help='ideal rows per shard'),
    min_rows: int = Opt(15_000_000, help='minumum rows per shard'),
    max_rows: int = Opt(20_000_000, help='maximum rows per shard')
):
    """
    Deploy the Sharding Recommender SpotApp.
    """
    ts = ctx.obj.thoughtspot

    parameters = {
        'parameter: CPU per Node': str(cpu_per_node),
        'parameter: Ideal Rows per Shard': str(ideal_rows),
        'parameter: Maximum Rows per Shard': str(max_rows),
        'parameter: Minimum Rows per Shard': str(min_rows),
        'parameter: Number of ThoughtSpot Nodes': str(nodes),
        'parameter: Unsharded Row Threshold': str(threshold)
    }

    here = pathlib.Path(__file__).parent
    tmls = []

    for file in here.glob("**/*.tml"):
        tml_cls = determine_tml_type(path=file)
        tml = tml_cls.load(file)
        tml.guid = None

        if isinstance(tml, Table):
            tml.table.db = falcon_database

        if isinstance(tml, Worksheet):
            for formula in tml.worksheet.formulas:
                try:
                    formula.expr = parameters[formula.name]
                except KeyError:
                    pass

        tmls.append(tml)

    r = ts.api.metadata_tml_import(import_objects=[t.dumps() for t in tmls], import_policy=TMLImportPolicy.all_or_none)

    from rich.align import Align
    from rich.table import Table as RichTable
    from rich import box

    status_emojis = {
        "OK": ":white_heavy_check_mark:",
        "WARNING": ":pinching_hand:",
        "ERROR": ":cross_mark:",
    }

    table = RichTable(width=150, box=box.SIMPLE_HEAD, row_styles=("dim", ""), title_style="white", caption_style="white")
    table.add_column("Status", justify="center", width=10)  # 4 + length of "status"
    table.add_column("Type", justify="center", width=13)    # 4 + length of "worksheet"
    table.add_column("GUID", justify="center", width=40)    # 4 + length of a guid
    table.add_column("Name", width=150 - 10 - 13 - 40, no_wrap=True)

    for tml, content in zip(tmls, r.json()["object"]):
        status = status_emojis.get(content["response"]["status"]["status_code"], ":cross_mark:")
        type_ = tml.tml_type_name
        guid = content["response"].get("header", {}).get("id_guid", "[gray]{null}")
        name = content["response"].get("header", {}).get("name", tml.name)

        table.add_row(status, type_, guid, name)

    rich_console.print(Align.center(table))


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

    with rich_console.status("[bold green]getting falcon table info"):
        r = _extended_rest_api_v1.periscope_sage_combined_table_info(ts.api)

        if not r.is_success:
            rich_console.error(f"could not get falcon table info {r}")
            raise typer.Exit(1)

        data = [FalconTableInfo.from_api_v1(_) for _ in r.json()["tables"]]

    with rich_console.status(f"[bold green]loading data to {syncer.name}.."):
        syncer.dump("ts_falcon_table_info", data=data)
