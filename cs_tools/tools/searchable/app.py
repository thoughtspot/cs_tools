import datetime as dt
import logging

from typer import Argument as A_, Option as O_  # noqa
import typer

from cs_tools.helpers.cli_ux import (
    console, frontend, CSToolsGroup, CSToolsCommand, SyncerProtocolType
)
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig

from . import transform


log = logging.getLogger(__name__)


app = typer.Typer(
    help="""
    Explore your ThoughtSpot metadata, in ThoughtSpot!
    """,
    cls=CSToolsGroup
)
