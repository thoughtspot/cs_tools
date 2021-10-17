import pathlib
import enum

from typer import Argument as A_, Option as O_  # noqa
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.settings import TSConfig
from cs_tools.thoughtspot import ThoughtSpot


class ContentType(enum.Enum):
    answer = 'answer'
    pinboard = 'pinboard'
    all = 'all'


app = typer.Typer(
    help="""
    Archiver.

    Solution should help the customer identify objects which have not
    been visited within a certain timeframe.
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def fetch(
    tag: str=O_(..., help='tag name to use for labeling objects to archive'),
    content: ContentType=O_('all', help=''),
    months: int=O_('all', help=''),
    dry_run: bool=O_(False, '--dry-run', help=''),
    **frontend_kw
):
    """
    Identify objects which objects can be archived.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as ts:
        ...


@app.command(cls=RichCommand)
@frontend
def annul(
    # tag: str=O_(),
    # dry_run: bool=O_(),
    **frontend_kw
):
    """
    Unarchive objects.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as ts:
        ...


@app.command(cls=RichCommand)
@frontend
def delete(
    # tag: str=O_(),
    # months: int=O_(),
    # export: pathlib.Path=O_(),
    # dry_run: bool=O_(),
    **frontend_kw
):
    """
    Remove objects from the platform.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as ts:
        ...
