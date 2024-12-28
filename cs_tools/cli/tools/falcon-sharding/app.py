from __future__ import annotations

import logging
import pathlib

from thoughtspot_tml import Table, Worksheet
from thoughtspot_tml.utils import determine_tml_type
import httpx
import typer

from cs_tools import utils
from cs_tools.api import workflows
from cs_tools.cli import progress as px
from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import CSToolsApp

from . import _private_api, models

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

    TOOL_TASKS = [
        px.WorkTask(id="CUSTOMIZE", description="Customizing Sharding Model to your cluster"),
        px.WorkTask(id="DEPLOY", description="Deploying TML to ThoughtSpot"),
    ]

    with px.WorkTracker("Deploying Sharding Recommender", tasks=TOOL_TASKS) as tracker:
        with tracker["CUSTOMIZE"]:
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

            for path in here.glob("**/*.tml"):
                tml_cls = determine_tml_type(path=path)
                tml = tml_cls.load(path)
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

        with tracker["DEPLOY"]:
            try:
                c = workflows.metadata.tml_import(tmls=tmls, policy="ALL_OR_NONE", timeout=60 * 15, http=ts.api)
                d = utils.run_sync(c)
            except httpx.HTTPError as e:
                log.error(f"Failed to call metadata/tml/import.. {e}")
                return 1

            for tml_import_info in d:
                idx = tml_import_info["request_index"]
                tml = tmls[idx]
                tml_type = tml.tml_type_name.upper()

                if tml_import_info["response"]["status"]["status_code"] == "OK":
                    log.info(f"{tml_type} '{tml.name}' successfully imported")

    return 0


@app.command(dependencies=[thoughtspot])
def gather(
    ctx: typer.Context,
    syncer: DSyncer = typer.Option(
        ...,
        help="protocol and path for options to pass to the syncer",
        metavar="protocol://DEFINITION.toml",
        click_type=SyncerProtocolType(models=[models.FalconTableInfo]),
    ),
):
    """
    Extract Falcon table info from your ThoughtSpot platform.
    """
    ts = ctx.obj.thoughtspot

    TOOL_TASKS = [
        px.WorkTask(id="COLLECT", description="Fetching data from ThoughtSpot"),
        px.WorkTask(id="CLEAN", description="Transforming API results"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {syncer.name}"),
    ]

    with px.WorkTracker("Deploying Searchable", tasks=TOOL_TASKS) as tracker:
        with tracker["COLLECT"]:
            c = _private_api.periscope_sage_combined_table_info(http=ts.api)
            r = utils.run_sync(c)

            if not r.is_success:
                log.error(f"could not get falcon table info {r}")
                return 1

        with tracker["CLEAN"]:
            renamed = [
                models.FalconTableInfo.validated_init(
                    **{
                        "table_guid": data["guid"],
                        "ip": "all" if data.get("ip") == -1 else data.get("ip", "all"),
                        "database_name": data.get("database"),
                        "schema_name": data.get("schema"),
                        "table_name": data.get("name"),
                        "state": data.get("state"),
                        "database_version": data.get("databaseVersion"),
                        "serving_version": data.get("servingVersion"),
                        "building_version": data.get("buildingVersion"),
                        "build_duration_s": data.get("buildDuration"),
                        "is_known": data.get("isKnown"),
                        "database_status": data.get("databaseStatus"),
                        "last_uploaded_at": data.get("lastUploadedAt", 0) / 1_000_000,
                        "num_of_rows": data.get("numOfRows"),
                        "approx_bytes_size": data.get("approxByteSize"),
                        "uncompressed_bytes_size": data.get("uncompressedByteSize"),
                        "row_skew": data.get("rowSkew"),
                        "num_shards": data.get("numShards"),
                        "csv_size_with_replication_mb": data.get("csvSizeWithReplicationMB"),
                        "replicated": data.get("replicated"),
                    }
                ).model_dump()
                for data in r.json()["tables"]
            ]

        with tracker["DUMP_DATA"]:
            syncer.dump("ts_falcon_table_info", data=renamed)

    return 0
