from typing import List
import pathlib
import enum

from typer import Argument as A_, Option as O_
import typer

from cs_tools.helpers.cli_ux import show_tool_options, frontend
from cs_tools.settings import TSConfig
from cs_tools.const import FMT_TSLOAD_DATETIME
from cs_tools.util.datetime import to_datetime
from cs_tools.api import ThoughtSpot


# DATA METHODS


def _to_friendly_name(metadata_type: str) -> str:
    """
    Translate internal names to something more end-user friendly.

    TODO: finalize and move to util.ux
    """
    mapping = {
        'QUESTION_ANSWER_BOOK': 'saved answer',
        'PINBOARD_ANSWER_BOOK': 'pinboard',
        'LOGICAL_TABLE': 'worksheet',
        'USER_DEFINED': 'imported table',
        'ONE_TO_ONE_LOGICAL': 'table',
        'AGGR_WORKSHEET': 'view',
        'INSIGHT': 'spotiq insight'
    }

    return mapping.get(metadata_type, metadata_type)


def _get_metadata(
    api: ThoughtSpot,
    *,
    metadata_types: List[str]=None
):
    """
    Return a flat data structure of metadata objects.

    Data returns about each object:
        - guid
        - type
        - name
        - author_name
        - author_display_name
        - created_at
        - modified_at
    """
    metadata = []

    for metadata_type in metadata_types:
        r = api._metadata.list(type=metadata_type, batchsize=-1, showhidden=False)
        data = r.json().get('headers', [])

        for point in data:
            metadata.append({
                'guid': point['id'],
                'type': _to_friendly_name(point['type']),
                'name': point['name'],
                'author_name': point['authorName'],
                'author_display_name': point['authorDisplayName'],
                'created_at': to_datetime(point['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                'modified_at': to_datetime(point['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME)
            })

    return metadata


# APP stuff


app = typer.Typer(
    help="""
    Get details about a given type of metadata object.

    Metadata objects are concepts in ThoughtSpot that store data. Things
    like worksheet, answers, pinboards.
    """,
    callback=show_tool_options,
)


class Metadata(str, enum.Enum):
    """
    CLI helper.
    """
    LOGICAL_TABLE = 'worksheet'
    PINBOARD_ANSWER_BOOK = 'pinboard'
    QUESTION_ANSWER_BOOK = 'answer'

    @classmethod
    def all(cls):
        """
        List all the choices for CLI.
        """
        choices = ' '.join(cls)
        return f'[{choices}]'


@app.command()
@frontend
def gather_data(
    types: List[Metadata]=A_(None, help='types of object to get  [default: worksheet]', metavar=Metadata.all()),
    filepath: pathlib.Path=O_(None, help='if specified, filepath to save data to'),
    create: bool=O_(True, '--create-tables', help='create tables in Falcon if they don\'t exist'),
    **frontend_kw
):
    """
    Gather and optionally, insert data into Falcon.

    By default, data is automatically gathered and inserted into the
    platform. If save_path argument is used, data will not be inserted
    and will instead be dumped to the location specified.
    """
    app_dir = pathlib.Path(typer.get_app_dir('cs_tools'))
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    if not types:
        types = [Metadata.LOGICAL_TABLE]

    if not filepath:
        filepath = app_dir / 'tmp_created_objects_data.csv'

    with ThoughtSpot(cfg) as api:
        data = _get_metadata(api, metadata_types=[m.name for m in types])
        _to_csv(data, fp=filepath)

        if filepath is not None:
            return

        # TODO: create tables
        # TODO: insert data
        # TODO: remove file ... filepath.unlink()
