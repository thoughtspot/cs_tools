from __future__ import annotations

import logging
import pathlib

from thoughtspot_tml import Table, Worksheet
from thoughtspot_tml.utils import determine_tml_type
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.layout import LiveTasks
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import CSToolsApp, rich_console
from cs_tools.types import TMLImportPolicy

from . import _extended_rest_api_v1, layout, models

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
    falcon_database: str = typer.Option("cs_tools", help="name of the database where data is gathered to"),
    nodes: int = typer.Option(..., help="number of nodes serving your ThoughtSpot cluster"),
    cpu_per_node: int = typer.Option(56, help="number of CPUs serving each node"),
    threshold: int = typer.Option(
        55_000_000, help="unsharded row threshold, once exceeded a table will be a candidate for sharding"
    ),
    ideal_rows: int = typer.Option(20_000_000, help="ideal rows per shard"),
    min_rows: int = typer.Option(15_000_000, help="minumum rows per shard"),
    max_rows: int = typer.Option(20_000_000, help="maximum rows per shard"),
):
    """
    Deploy the Sharding Recommender SpotApp.
    """
    ts = ctx.obj.thoughtspot

    tasks = [
        ("customize_spotapp", "Customizing [b blue]Falcon Table Sharding Worksheet[/] with your parameters"),
        ("deploy_spotapp", "Deploying the SpotApp to ThoughtSpot"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:
        with tasks["customize_spotapp"]:
            parameters = {
                "parameter: CPU per Node": str(cpu_per_node),
                "parameter: Ideal Rows per Shard": str(ideal_rows),
                "parameter: Maximum Rows per Shard": str(max_rows),
                "parameter: Minimum Rows per Shard": str(min_rows),
                "parameter: Number of ThoughtSpot Nodes": str(nodes),
                "parameter: Unsharded Row Threshold": str(threshold),
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

        with tasks["deploy_spotapp"]:
            response = ts.tml.to_import(tmls, policy=TMLImportPolicy.all_or_none)

    status_emojis = {"OK": ":white_heavy_check_mark:", "WARNING": ":pinching_hand:", "ERROR": ":cross_mark:"}
    centered_table = layout.build_table()

    for r in response:
        status = status_emojis.get(r.status_code, ":cross_mark:")
        guid = r.guid or "[gray]{null}"
        centered_table.renderable.add_row(status, r.tml_type_name, guid, r.name)

    rich_console.print(centered_table)


@app.command(dependencies=[thoughtspot])
def gather(
    ctx: typer.Context,
    syncer: DSyncer = typer.Option(
        ...,
        help="protocol and path for options to pass to the syncer",
        metavar="protocol://DEFINITION.toml",
        custom_type=SyncerProtocolType(models=[models.FalconTableInfo]),
    ),
):
    """
    Extract Falcon table info from your ThoughtSpot platform.
    """
    ts = ctx.obj.thoughtspot

    tasks = [
        ("gather_info", "Getting Falcon table information"),
        ("dump_info", f"Writing table information to {syncer.name}"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:
        with tasks["gather_info"]:
            r = _extended_rest_api_v1.periscope_sage_combined_table_info(ts.api.v1)

            if not r.is_success:
                rich_console.error(f"could not get falcon table info {r}")
                raise typer.Exit(1)

            data = [models.FalconTableInfo.from_api_v1(_) for _ in r.json()["tables"]]

        with tasks["dump_info"]:
            syncer.dump("ts_falcon_table_info", data=data)
