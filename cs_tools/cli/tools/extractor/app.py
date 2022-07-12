import logging

from typer import Argument as A_, Option as O_  # noqa
import typer

from cs_tools.cli.tools.common import setup_thoughtspot, teardown_thoughtspot
from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand

from .enums import RecordsetType


log = logging.getLogger(__name__)


app = typer.Typer(
    help="""
    Extract data from a worksheet, view, or table in your platform.
    """,
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
@depends(
    'thoughtspot',
    setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
)
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

    Columns must be surrounded by square brackets. Search-level formulas are
    not currently supported, but a formula defined as part of a data source is.
    """
    ts = ctx.obj.thoughtspot

    with console.status(f'[bold green]retrieving data from {data_type.value} "{dataset}"..[/]'):
        data = ts.search(query, **{data_type.value: dataset})

    syncer.dump(target, data=data)
