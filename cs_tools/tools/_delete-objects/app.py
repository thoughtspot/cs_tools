# DEV NOTE:
#
import pathlib

from typer import Argument as A_, Option as O_  # noqa
import typer

from cs_tools.helpers.cli_ux import RichGroup, RichCommand, frontend, console
from cs_tools.settings import TSConfig
from cs_tools.api import ThoughtSpot


app = typer.Typer(
    help="""
    Tool takes an input file and or a specific obejct and deletes it from the meta data.
    This tool leverages the /metadata/delete private API endpoint

    Valid metadata object type values are:
    QUESTION_ANSWER_BOOK
    PINBOARD_ANSWER_BOOK
    QUESTION_ANSWER_SHEET
    PINBOARD_ANSWER_SHEET
    LOGICAL_COLUMN (Not Supported)
    LOGICAL_TABLE (Not Supported)
    LOGICAL_RELATIONSHIP (Not Supported)
    TAG (Not Supported)
    DATA_SOURCE (Not Supported)
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def object(
    type: str=A_(..., help='lorem ipsum, metadata type'),
    guid: str=A_(..., help='lorem ipsum, guid to delete'),
    **frontend_kw
):
    """
    Removes a specific object from ThoughtSpot metadata given the type and guid

    extra info here
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as api:
        console.print(f'deleting object .. {type} ... {guid} ... ')
        r = api._metadata.delete(type=type, id=[guid])

        console.print(r)
        console.print(r.json())


# Print line deleting object GUID X, Name Y
# Call Delete Object Private API call
@app.command(cls=RichCommand)
@frontend
def from_file(
    # file: pathlib.Path=A_(..., help='lorem ipsum'),
    file: pathlib.Path=O_(..., help='path to xlsx file with columns type and guid'),
    **frontend_kw
):
    """
    Removes a list of objects from ThoughtSpot metadata given an input xlxs file with headers type, guid

    extra info
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    # Read info from command line input
    # Open Excel input (or read single from command line)
    # Loop through lines of excel

    data = [  # data gotten from XLSX
        {'type': 'answer', 'guid': 'guid1'},
        {'type': 'answer', 'guid': 'guid2'},
        {'type': 'pinboard', 'guid': 'guid6'},
        {'type': 'pinboard', 'guid': 'guid7'},
        {'type': 'answer', 'guid': 'guid3'},
        {'type': 'answer', 'guid': 'guid4'},
        {'type': 'pinboard', 'guid': 'guid5'}
    ]

    with ThoughtSpot(cfg) as api:
        ...



