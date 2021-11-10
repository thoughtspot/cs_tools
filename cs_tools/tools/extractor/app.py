import logging
import pathlib

from typer import Argument as A_, Option as O_  # noqa
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig
from cs_tools.tools import common

from .enums import RecordsetType


log = logging.getLogger(__name__)


app = typer.Typer(
    help="""
    Extract data from a worksheet, view, or table in your platform.

    By default, the system adoption worksheet "TS: BI Server" will only store 6
    months worth of user activity. While this can be configurable on the
    ThoughtSpot backend, it's also possible to extract this data set, load it
    into an Embrace-connected CDW, and then re-expose it to ThoughtSpot to
    maintain the historicals indefinitely.
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def search(
    query: str = O_(..., help='search terms to issue against the dataset'),
    dataset: str = O_(..., help='name of the worksheet, view, or table to search against'),
    export: pathlib.Path = O_(..., help='full path to save data set to', dir_okay=False, resolve_path=True),
    data_type: RecordsetType = O_('worksheet', help='type of object to search'),
    **frontend_kw
):
    """
    Search a dataset from the command line.

    Columns must be surrounded by square brackets. Search-level formulas are
    not currently supported, but a formula defined as part of a data source is.

    [b yellow]There is a hard limit of 100K rows extracted for any given Search.[/]

    \b
    Further reading:
      https://docs.thoughtspot.com/software/latest/search-data-api
      https://docs.thoughtspot.com/software/latest/search-data-api#components
      https://docs.thoughtspot.com/software/latest/search-data-api#_limitations_of_search_query_api
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as ts:
        with console.status(f'[bold green]retrieving data from {data_type.value} "{dataset}"..[/]'):
            data = ts.search(query, **{data_type.value: dataset})

    common.to_csv(data, export, header=True)
