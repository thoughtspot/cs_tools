from __future__ import annotations

import functools as ft

import typer

from cs_tools import _types, utils
from cs_tools.api import workflows
from cs_tools.cli import (
    custom_types,
    progress as px,
)
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.ux import AsyncTyper
from cs_tools.sync.base import DatabaseSyncer, Syncer

app = AsyncTyper(help="Extract data from a worksheet, view, or table in ThoughtSpot.")


@app.callback()
def _noop(ctx: typer.Context) -> None:
    """Just here so that no_args_is_help=True works on a single-command Typer app."""


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def search(
    ctx: typer.Context,
    identifier: _types.ObjectIdentifier = typer.Option(..., help="name or guid of the dataset to extract data from"),
    search_tokens: str = typer.Option(..., help="search terms to issue against the dataset"),
    syncer: Syncer = typer.Option(
        ...,
        click_type=custom_types.Syncer(),
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

    CLUSTER_TIMEZONE = ts.session_context.thoughtspot.timezone

    TOOL_TASKS = [
        px.WorkTask(id="SEARCH", description="Fetching data from ThoughtSpot"),
        px.WorkTask(id="CLEAN", description="Transforming API results"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {syncer.name}"),
    ]

    with px.WorkTracker("Extracting Data", tasks=TOOL_TASKS) as tracker:
        with tracker["SEARCH"]:
            c = workflows.search(worksheet=identifier, query=search_tokens, timezone=CLUSTER_TIMEZONE, http=ts.api)
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

            if isinstance(syncer, DatabaseSyncer):
                Model = utils.create_dynamic_model(target, sample_row=reshaped[0])
                Model.__table__.to_metadata(syncer.metadata, schema=None)
                syncer.metadata.create_all(syncer.engine, tables=[Model.__table__])

        with tracker["DUMP_DATA"]:
            syncer.dump(target, data=reshaped)
