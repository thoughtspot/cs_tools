from __future__ import annotations

import logging

import typer

from cs_tools._compat import StrEnum
from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.layout import LiveTasks
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import CSToolsApp, rich_console

from . import work

log = logging.getLogger(__name__)
app = CSToolsApp(help="Extract data from a worksheet, view, or table in ThoughtSpot.")


class SearchableDataSource(StrEnum):
    worksheet = "worksheet"
    table = "table"
    view = "view"


@app.command(dependencies=[thoughtspot])
def search(
    ctx: typer.Context,
    query: str = typer.Option(..., help="search terms to issue against the dataset"),
    dataset: str = typer.Option(..., help="name of the worksheet, view, or table to search against"),
    data_type: SearchableDataSource = typer.Option("worksheet", help="type of object to search"),
    syncer: DSyncer = typer.Option(
        ...,
        click_type=SyncerProtocolType(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    target: str = typer.Option(..., help="directive to load Search data to", rich_help_panel="Syncer Options"),
):
    """
    Search a dataset from the command line.

    Columns must be surrounded by square brackets and fully enclosed by quotes.
    Search-level formulas are not currently supported, but a formula defined as
    part of a data source is.

    If the syncer target is a database table that does not exist, we'll create it.
    """
    ts = ctx.obj.thoughtspot

    tasks = [
        ("gather_search", f"Retrieving data from [b blue]{data_type.value.title()} [b green]{dataset}"),
        ("syncer_dump", f"Writing rows to [b blue]{syncer.name}"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:
        with tasks["gather_search"]:
            data = ts.search(query, **{data_type: dataset})

        if not data:
            rich_console.log("[red]No data returned from query:[/] " + rf"{query}")
            return

        with tasks["syncer_dump"]:
            if hasattr(syncer, "__is_database__"):
                table = work.infer_schema_from_results(data, tablename=target, metadata=syncer.metadata)
                syncer.metadata.create_all(bind=syncer.cnxn, tables=[table])

                # fix data for INSERT
                column_names = [c.name for c in table.columns]
                data = [dict(zip(column_names, row.values())) for row in data]

            syncer.dump(target, data=data)
