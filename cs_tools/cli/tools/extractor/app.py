from typing import Any, Dict
import datetime as dt
import logging
import re

from typer import Argument as A_, Option as O_  # noqa
import sqlalchemy as sa
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import console, CSToolsApp

from .enums import RecordsetType


log = logging.getLogger(__name__)
RE_LETTERS_ONLY = re.compile(r'[^A-Za-z]')


def infer_schema_from_results(data: Dict[str, Any], tablename: str, metadata: sa.Table) -> sa.Table:
    """
    """
    PY_TO_SQL_MAPPING_TYPES = {
        str: sa.String,
        bool: sa.Boolean,
        float: sa.Float,
        int: sa.Integer,
        dt.date: sa.Date,
        dt.datetime: sa.DateTime,
    }

    columns = []

    for key in data[0].keys():
        max_val = max(row[key] for row in data)
        column_name = RE_LETTERS_ONLY.sub("_", key).lower()
        column_type = PY_TO_SQL_MAPPING_TYPES.get(type(max_val), sa.String)

        if column_type == sa.Float:
            p, _, s = str(max_val).partition(".")
            column_type = column_type(precision=len(p) + len(s))

        if column_type == sa.Integer and max_val > (2 ** 31 - 1):
            column_type = sa.BigInteger

        column = sa.Column(column_name, column_type)
        columns.append(column)

    return sa.Table(tablename, metadata, *columns)


app = CSToolsApp(help="Extract data from a worksheet, view, or table in your platform.")


@app.command(dependencies=[thoughtspot])
def search(
    ctx: typer.Context,
    query: str = O_(..., help='search terms to issue against the dataset'),
    dataset: str = O_(..., help='name of the worksheet, view, or table to search against'),
    syncer: str = O_(
        ...,
        help='protocol and path for options to pass to the syncer',
        metavar='protocol://DEFINITION.toml',
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    ),
    target: str = O_(..., help='syncer directive to load data to'),
    data_type: RecordsetType = O_('worksheet', help='type of object to search')
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
