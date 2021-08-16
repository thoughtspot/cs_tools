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

    QUESTION_ANSWER_BOOK, 
    PINBOARD_ANSWER_BOOK, 
    QUESTION_ANSWER_SHEET, 
    PINBOARD_ANSWER_SHEET, 
    LOGICAL_COLUMN (Not Supported),
    LOGICAL_TABLE (Not Supported),
    LOGICAL_RELATIONSHIP (Not Supported),
    TAG (Not Supported),
    DATA_SOURCE (Not Supported)


    csv file format:

    type,guid

    QUESTION_ANSWER_BOOK,guid1

    PINBOARD_ANSWER_BOOK,guid2


    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def object(
    type: str=A_(..., help='string, metadata type'),
    guid: str=A_(..., help='string, guid to delete'),
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

        #console.print(r)
        #console.print(r.json())

@app.command(cls=RichCommand)
@frontend
def from_file(
    file: pathlib.Path=O_(..., help='path to file with columns: type and guid'),
    **frontend_kw
    # ToDo: Need to add error handling if file is not found
):
    """
    Removes a list of objects from ThoughtSpot metadata given an input .csv file with headers type, guid

    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    
    #ToDo: Add handling to Open Excel input (or read single from command line)

    with open(file, newline='') as TsObjectCsv:
        TsObjectData = csv.DictReader(TsObjectCsv) 
        
        

        with ThoughtSpot(cfg) as api:
            
        # iterate over the list (aka array) #=> data
            for ts_object in TsObjectData:
                # console.print(ts_object)

                type_ = ts_object['type']
                guid = ts_object['guid']

                console.print(f'deleting object .. {type_} ... {guid} ... ')

                r = api._metadata.delete(type=type_, id=[guid])

                ##console.print(r)
                ##console.print(r.json())


