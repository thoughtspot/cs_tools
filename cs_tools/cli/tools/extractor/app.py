from typing import Dict, Any
import datetime as dt
import logging
import re

from typer import Argument as A_  # noqa
from typer import Option as O_
import sqlalchemy as sa
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import console
from cs_tools.cli.ux import CSToolsArgument as Arg
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import CSToolsApp

from .enums import RecordsetType

log = logging.getLogger(__name__)


app = CSToolsApp(help="Extract data from a worksheet, view, or table in your platform.")


@app.command(dependencies=[thoughtspot])
def search(
    ctx: typer.Context,
    query: str = Opt(..., help="search terms to issue against the dataset"),
    dataset: str = Opt(..., help="name of the worksheet, view, or table to search against"),
    syncer: str = Opt(
        ...,
        help="protocol and path for options to pass to the syncer",
        metavar="protocol://DEFINITION.toml",
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx),
    ),
    target: str = Opt(..., help="syncer directive to load data to"),
    data_type: RecordsetType = Opt("worksheet", help="type of object to search"),
):
    """
    Search a dataset from the command line.

    Columns must be surrounded by square brackets and fully enclosed by quotes.
    Search-level formulas are not currently supported, but a formula defined as
    part of a data source is.

    If the syncer target is a database table and does not exist, we'll create it.
    """
    with console.status(f'[bold green]retrieving data from {data_type.value} "{dataset}"..[/]'):
        data = ctx.obj.thoughtspot.search(query, **{data_type.value: dataset})

    if not data:
        query = query.replace("[", r"\[")
        console.log(f"[red]No data returned from query:[/] {query}")
        return

    if hasattr(syncer, "__is_database__"):
        table = infer_schema_from_results(data, tablename=target, metadata=syncer.metadata)
        syncer.metadata.create_all(bind=syncer.cnxn, tables=[table])

        # fix data for INSERT
        column_names = [c.name for c in table.columns]
        data = [dict(zip(column_names, row.values())) for row in data]

    syncer.dump(target, data=data)
