from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy.schema import Column
from sqlalchemy.types import BigInteger, Boolean, Date, DateTime, Float, SmallInteger, Text
from sqlmodel import Field, SQLModel
import pydantic
import typer

from cs_tools._compat import StrEnum
from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.layout import LiveTasks
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import CSToolsApp, rich_console

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
    date_partition_by: str = typer.Option(None, help="DATE or DATE_TIME column to partition by"),
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
            search_kwargs = {data_type: dataset, "use_logical_column_names": True, "include_dtype_mapping": True}
            data, column_mapping = ts.search(query, **search_kwargs)

            renamed = []
            curr_date, sk_idx = None, 0

            for row in data:
                row_date = row[date_partition_by].replace(tzinfo=dt.timezone.utc).date() if date_partition_by else None

                # reset the surrogate key every day
                if curr_date != row_date:
                    curr_date = row_date
                    sk_idx = 0

                sk_idx += 1

                renamed.append(
                    {
                        "sk_dummy": f"{ts.session_context.thoughtspot.cluster_id}-{row_date}-{sk_idx}",
                        "cluster_guid": ts.session_context.thoughtspot.cluster_id,
                        **row,
                    }
                )

            if sql_friendly_names:
                # Replace spaces with underscores, and lowercase everything
                renamed = [{k.lower().replace(" ", "_"): v for k, v in row.items()} for row in renamed]
                column_mapping = {k.lower().replace(" ", "_"): v for k, v in column_mapping.items()}

            if syncer.is_database_syncer:
                field_defs: dict[str, tuple[type, Field]] = {
                    # Mark the SK as the PrimaryKey
                    "sk_dummy": (str, Field(sa_column=Column(Text, primary_key=True))),
                    "cluster_guid": (str, Field(sa_column=Column(Text, primary_key=True))),
                }

                sqla_types = {
                    "CHAR": Text,
                    "BOOL": Boolean,
                    "FLOAT": Float,
                    "INT32": SmallInteger,
                    "INT64": BigInteger,
                    "DATE": Date,
                    "DATE_TIME": DateTime,
                }

                # Compute the column definitions
                for column, ts_generic_type in column_mapping.items():
                    if column == "sk_dummy":
                        continue

                    # Fetch the python type
                    py_type = type(renamed[0][column])

                    # Fetch the complementary sqlalchemy type
                    sa_type = sqla_types.get(ts_generic_type, None)

                    if sa_type is None:
                        log.warning(f"Unknown type: {ts_generic_type} for column: {column}, falling back to VARCHAR..")
                        sa_type = Text

                    # Build and assign the sqlmodel.Field definition
                    is_pk = column in ("sk_dummy", date_partition_by)

                    field_defs[column] = (
                        py_type,
                        Field(
                            ... if is_pk else None,
                            sa_column=Column(name=column, type_=sa_type, primary_key=is_pk),
                        ),
                    )

                # Create the dynamic table
                model = pydantic.create_model(target, __base__=SQLModel, __cls_kwargs__={"table": True}, **field_defs)
                model.__table__.to_metadata(syncer.metadata, schema=None)
                syncer.metadata.create_all(syncer.engine, tables=list(syncer.metadata.sorted_tables))

        with tasks["syncer_dump"]:
            syncer.dump(target.lower(), data=renamed)
