# DEV NOTE:
#
import pathlib
import csv

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


    csv file format:
    type,guid
    QUESTION_ANSWER_SHEET,guid1
    PINBOARD_ANSWER_SHEET,guid2


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
    file: pathlib.Path=O_(..., help='path to file with columns: type and guid'),
    **frontend_kw
    # ToDo: Need to add error handling if file is not found
):
    """
    Removes a list of objects from ThoughtSpot metadata given an input xlxs file with headers type, guid

    extra info
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    # Read info from command line input
    # Open Excel input (or read single from command line)
    # Loop through lines of excel
    # print_str = f'Trying to Open  file {file}'
    # console.print(print_str) 

    with open(file, newline='') as TsObjectCsv:
        TsObjectData = csv.DictReader(TsObjectCsv) 
        
        
        # data = [  # data gotten from XLSX
        #     {
        #         'type': 'answer',
        #         'guid': 'guid1'
        #     },
        #     {'type': 'answer', 'guid': 'guid2'},
        #     {'type': 'pinboard', 'guid': 'guid6'},
        #     {'type': 'pinboard', 'guid': 'guid7'},
        #     {'type': 'answer', 'guid': 'guid3'},
        #     {'type': 'answer', 'guid': 'guid4'},
        #     {'type': 'pinboard', 'guid': 'guid5'}
        # ]

        with ThoughtSpot(cfg) as api:
            
        # iterate over the list (aka array) #=> data
            for ts_object in TsObjectData:
                console.print(ts_object)

                # grab key or value from each dictionary (aka hash-map)
                # ts_object['type']     #=> 'answer'
                # ts_object.get('type') #=> 'answer'

                type_ = ts_object['type']
                guid = ts_object['guid']
                print_str = f'deleting guid {guid} of type {type_}'

                console.print(print_str)

                r = api._metadata.delete(type=type_, id=[guid])

                ##console.print(r)
                ##console.print(r.json())


