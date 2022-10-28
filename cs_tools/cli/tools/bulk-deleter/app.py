import logging
import pathlib
import enum

from typer import Argument as A_, Option as O_  # noqa
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import SyncerProtocolType
from cs_tools.cli.ux import console, CSToolsApp, CSToolsGroup
from cs_tools.util import chunks


log = logging.getLogger(__name__)
HERE = pathlib.Path(__file__).parent


class AcceptedObjectType(str, enum.Enum):
    QUESTION_ANSWER_BOOK = 'saved answer'
    PINBOARD_ANSWER_BOOK = 'pinboard'
    saved_answer = 'QUESTION_ANSWER_BOOK'
    liveboard = 'PINBOARD_ANSWER_BOOK'
    pinboard = 'PINBOARD_ANSWER_BOOK'

    def to_system_type(self) -> str:
        return self.name if self.name.endswith('BOOK') else self.value

    def __eq__(self, other) -> bool:
        if hasattr(other, 'value'):
            other = other.value

        return other in (self.value, self.name)


def _validate_objects_exist(ts, data):
    """
    /metadata/delete WILL NOT fail on ValueError.

    As long as valid UUID4s are passed, and valid types are passed, the
    endpoint will happily return. If content does not exist, or if the
    wrong type for GUIDs is passed, ThoughtSpot will attempt to delete the
    objects.

    What this means is you could potentially delete an object you didn't
    mean to delete.. so this filters those objects out.

    This is a ThoughtSpot API limitation.
    """
    new_data = {
        'QUESTION_ANSWER_BOOK': [],
        'PINBOARD_ANSWER_BOOK': []
    }

    for object_ in data:
        system_type = AcceptedObjectType(object_['object_type']).to_system_type()
        new_data[system_type].append(object_['object_guid'])

    for system_type, to_delete_guids in new_data.items():
        for chunk in chunks(to_delete_guids, n=15):
            r = ts.api.metadata.list_object_headers(type=system_type, fetchids=chunk)
            returned_guids = [_['id'] for _ in r.json()]

            if len(returned_guids) != len(chunk):
                for guid in set(to_delete_guids).difference(set(returned_guids)):
                    new_data[system_type].remove(guid)
                    log.warning(
                        f'{guid} [yellow]is not a valid [blue]{system_type}[/]![/] '
                        f'[error]removing this from the delete operation[/]'
                    )

    return new_data['QUESTION_ANSWER_BOOK'], new_data['PINBOARD_ANSWER_BOOK']


app = CSToolsApp(
    help="""Bulk delete metadata objects from your ThoughtSpot platform.""",
    cls=CSToolsGroup,
    options_metavar='[--version, --help]',
)


@app.command(dependencies=[thoughtspot])
def single(
    ctx: typer.Context,
    type: AcceptedObjectType = O_(..., help='type of the metadata to delete'),
    guid: str = O_(..., help='guid to delete')
):
    """
    Removes a specific object from ThoughtSpot.
    """
    ts = ctx.obj.thoughtspot
    system_type = AcceptedObjectType.to_system_type(type)

    data = [{'object_type': system_type, 'object_guid': guid}]
    answers, liveboards = _validate_objects_exist(ts, data)

    if not answers and not liveboards:
        raise typer.Exit(-1)

    console.print(f'deleting {system_type}: {guid}')
    r = ts.api._metadata.delete(type=system_type, id=[guid])
    log.debug(f'{r} - {r.content}')


@app.command(dependencies=[thoughtspot])
def from_tabular(
    ctx: typer.Context,
    syncer: str = O_(
        None,
        help='protocol and path for options to pass to the syncer',
        metavar='protocol://DEFINITION.toml',
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    ),
    deletion: str = O_(
        None,
        help='if using --syncer, directive to find user deletion at'
    ),
    batchsize: int = O_(1, help='maximum amount of objects to delete simultaneously')
):
    """
    Remove many objects from ThoughtSpot.

    Objects to delete are limited to answers and liveboards, but can follow
    either naming convention of internal API type, or the name found in the
    user interface.

    \b
    If you are deleting from an external data source, your data must follow the
    tabular format below.

    \b
        +-----------------------+-------------+
        | object_type           | object_guid |
        +-----------------------+-------------+
        | saved answer          | guid1       |
        | pinboard              | guid2       |
        | liveboard             | guid3       |
        | ...                   | ...         |
        | QUESTION_ANSWER_BOOK  | guid4       |
        | PINBOARD_ANSWER_BOOK  | guid5       |
        | ...                   | ...         |
        +-----------------------+-------------+
    """
    if syncer is not None and deletion is None:
        console.print('[red]you must provide a syncer directive to --deletion')
        raise typer.Exit(-1)

    ts = ctx.obj.thoughtspot
    data = syncer.load(deletion)

    answers, liveboards = _validate_objects_exist(ts, data)

    if liveboards:
        console.print(f'deleting {len(liveboards)} total liveboards')

        for chunk in chunks(liveboards, n=batchsize):
            if batchsize > 1:
                console.print(f'\tdeleting {len(chunk)} liveboards:\n{chunk}')

            r = ts.api._metadata.delete(type='PINBOARD_ANSWER_BOOK', id=list(chunk))
            log.debug(f'{r} - {r.content}')

    if answers:
        console.print(f'deleting {len(answers)} total answers')

        for chunk in chunks(answers, n=batchsize):
            if batchsize > 1:
                console.print(f'\tdeleting {len(chunk)} answers:\n{chunk}')

            r = ts.api._metadata.delete(type='QUESTION_ANSWER_BOOK', id=list(chunk))
            log.debug(f'{r} - {r.content}')
