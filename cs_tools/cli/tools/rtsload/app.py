from __future__ import annotations

import logging

import typer

from cs_tools import _types, utils
from cs_tools.api import workflows
from cs_tools.cli import custom_types
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper
from cs_tools.sync.base import Syncer
from cs_tools.sync.falcon.syncer import Falcon

_LOG = logging.getLogger(__name__)
app = AsyncTyper(
    help="""
    Enable loading files to ThoughtSpot from a remote machine.

    \b
    For further information on tsload, please refer to:
      https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
      https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
      https://docs.thoughtspot.com/latest/reference/data-importer-ref.html
    """,
)


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def status(ctx: typer.Context, cycle_id: str = typer.Argument(..., help="The dataload cycle id.")) -> _types.ExitCode:
    """Get the status of a data load."""
    ts = ctx.obj.thoughtspot

    with RICH_CONSOLE.status("[fg-success]Waiting for data load to complete.."):
        c = workflows.tsload.wait_for_dataload_completion(cycle_id=cycle_id, http=ts.api)

        status_data = utils.run_sync(c)

    return int(status_data["status"]["code"] == "SUCCESS")  # type: ignore[return-value]


@app.command(name="file", hidden=True)
@app.command(name="load-file")
@depends_on(thoughtspot=ThoughtSpot())
def load_file(
    ctx: typer.Context,
    input_syncer: Syncer = typer.Option(
        ...,
        click_type=custom_types.Syncer(),
        help="protocol and path for options to pass to the syncer",
    ),
    source_table: str = typer.Option(
        ...,
        help="Specifies the target table in Falcon.",
    ),
    falcon_syncer: Falcon = typer.Option(
        None,
        click_type=custom_types.Syncer(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    target_table: str = typer.Option(
        ..., help="Specifies the target table in Falcon.", rich_help_panel="Syncer Options"
    ),
) -> _types.ExitCode:
    """Load data to the remote tsload service."""
    ts = ctx.obj.thoughtspot

    if falcon_syncer is None:
        falcon_syncer = Falcon(database="cs_tools", thoughtspot=ts, wait_for_dataload_completion=True)
        _LOG.warning(f"No falcon_syncer provided, using default syncer.\n{falcon_syncer}")

    with RICH_CONSOLE.status(f"[fg-success]Loading [fg-warn]{input_syncer}[/] to ThoughtSpot.."):
        # LOAD THE DATA FROM THE INPUT SYNCER.
        data = input_syncer.load(source_table)

        # CREATE THE TABLE IN FALCON.
        Model = utils.create_dynamic_model(target_table, sample_row=data[0])
        assert hasattr(Model, "__table__"), "Dynamic model is not a proper SQLModel."
        Model.__table__.to_metadata(falcon_syncer.metadata, schema=None)
        falcon_syncer.metadata.create_all(falcon_syncer.engine, tables=[Model.__table__])

        # DUMP THE DATA TO FALCON.
        falcon_syncer.dump(target_table, data=data)

    return 0
