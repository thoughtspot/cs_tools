from __future__ import annotations

import functools as ft
import logging

import typer

from cs_tools import types, utils
from cs_tools.api import workflows
from cs_tools.cli import progress as px
from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import CSToolsApp

log = logging.getLogger(__name__)
app = CSToolsApp(help="Extract data from a worksheet, view, or table in ThoughtSpot.")


@app.callback()
def _noop(ctx: typer.Context) -> None:
    """Just here so that no_args_is_help=True works on a single-command Typer app."""


@app.command(dependencies=[thoughtspot])
def search(
    ctx: typer.Context,
    identifier: types.ObjectIdentifier = typer.Option(..., help="name or guid of the dataset to extract data from"),
    search_tokens: str = typer.Option(..., help="search terms to issue against the dataset"),
    syncer: DSyncer = typer.Option(
        ...,
        click_type=SyncerProtocolType(models=[]),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    target: str = typer.Option(..., help="directive to load Search data to", rich_help_panel="Syncer Options"),
    sql_friendly_names: bool = typer.Option(
        True,
        "--friendly-names / --original-names",
        help="if friendly, converts column names to a sql-friendly variant (lowercase & underscores)",
    ),
):
    """
    Search a dataset from the command line.

    Columns must be surrounded by square brackets and fully enclosed by quotes.
    Search-level formulas are not currently supported, but a formula defined as
    part of a data source is.

    If the syncer target is a database table that does not exist, we'll create it.
    """
    ts = ctx.obj.thoughtspot

    TOOL_TASKS = [
        px.WorkTask(id="SEARCH", description="Fetching data from ThoughtSpot"),
        px.WorkTask(id="CLEAN", description="Transforming API results"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {syncer.name}"),
    ]

    with px.WorkTracker("Extracting Data", tasks=TOOL_TASKS) as tracker:
        with tracker["SEARCH"]:
            c = workflows.search(worksheet=identifier, query=search_tokens, http=ts.api)
            _ = utils.run_sync(c)

        with tracker["CLEAN"]:
            reshaped = [
                {
                    "cluster_guid": ts.session_context.thoughtspot.cluster_id,
                    "sk_dummy": f"{ts.session_context.thoughtspot.cluster_id}-{idx}",
                    **row,
                }
                for idx, row in enumerate(_)
            ]

            if sql_friendly_names:
                FX_SANITIZE = ft.partial(lambda s: s.replace(" ", "_").casefold())
                reshaped = [{FX_SANITIZE(k): v for k, v in row.items()} for row in reshaped]

            if syncer.is_database_syncer:
                Model = utils.create_dynamic_model(target, sample_row=reshaped[0])
                Model.__table__.to_metadata(syncer.metadata, schema=None)
                syncer.metadata.create_all(syncer.engine, tables=[Model.__table__])

        with tracker["DUMP_DATA"]:
            syncer.dump(target, data=reshaped)
