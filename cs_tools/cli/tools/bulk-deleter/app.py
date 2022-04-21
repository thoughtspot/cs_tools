import logging
import pathlib
import enum

from typer import Argument as A_, Option as O_  # noqa
import typer

from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT
from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand, SyncerProtocolType
from cs_tools.cli.tools.common import setup_thoughtspot
from cs_tools.util import chunks


log = logging.getLogger(__name__)
HERE = pathlib.Path(__file__).parent


class ReversibleSystemType(str, enum.Enum):
    """
    Reversible mapping of system to friendly names.
    """
    PINBOARD_ANSWER_BOOK = 'pinboard'
    pinboard = 'PINBOARD_ANSWER_BOOK'
    QUESTION_ANSWER_BOOK = 'saved answer'
    saved_answer = 'QUESTION_ANSWER_BOOK'

    @classmethod
    def to_friendly(cls, value) -> str:
        value = value.strip()

        if '_' not in value:
            return value

        return getattr(cls, value).value

    @classmethod
    def to_system(cls, value) -> str:
        value = value.strip()

        if '_' in value:
            return value

        return getattr(cls, value.replace(' ', '_')).value


app = typer.Typer(
    help="""Bulk delete metadata objects from your ThoughtSpot platform.""",
    cls=CSToolsGroup,
    options_metavar='[--version, --help]',
)


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def single(
    ctx: typer.Context,
    type: ReversibleSystemType = O_(..., help='type of the metadata to delete'),
    guid: str = O_(..., help='guid to delete')
):
    """
    Removes a specific object from ThoughtSpot.
    """
    ts = ctx.obj.thoughtspot
    type = ReversibleSystemType.to_system(type.value)

    console.print(f'deleting object .. {type} ... {guid} ... ')

    # NOTE: /metadata/delete WILL NOT error if content does not exist, or if the
    # wrong type & guid are passed. This is a ThoughtSpot API limitation.
    r = ts.api._metadata.delete(type=type, id=[guid])
    log.debug(f'{r} - {r.content}')


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
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

    \b
    If you are deleting from an external data source, your data must follow the
    tabular format below.

    \b
        +----------------+-------+
        | type           | guid  |
        +----------------+-------+
        | saved answer   | guid1 |
        | pinboard       | guid2 |
        | ...            | ...   |
        | saved answer   | guid3 |
        +----------------+-------+
    """
    if syncer is not None:
        if deletion is None:
            console.print('[red]you must provide a syncer directive to --deletion')
            raise typer.Exit(-1)

    ts = ctx.obj.thoughtspot
    data = syncer.load(deletion)

    #
    # Delete Pinboards
    #
    guids = [_['guid'] for _ in data if ReversibleSystemType.to_friendly(_['type']) == 'pinboard']

    if guids:
        console.print(f'deleting {len(guids)} pinboards')

    for chunk in chunks(guids, n=batchsize):
        if batchsize > 1:
            console.print(f'    deleting {len(chunk)} pinboards')
            log.debug(f'    guids: {chunk}')

        r = ts.api._metadata.delete(type='PINBOARD_ANSWER_BOOK', id=list(chunk))
        log.debug(f'{r} - {r.content}')

    #
    # Delete Answers
    #
    guids = [_['guid'] for _ in data if ReversibleSystemType.to_friendly(_['type']) == 'saved answer']

    if guids:
        console.print(f'deleting {len(guids)} answers')

    for chunk in chunks(guids, n=batchsize):
        if batchsize > 1:
            console.print(f'    deleting {len(chunk)} answers')
            log.debug(f'    guids: {chunk}')

        r = ts.api._metadata.delete(type='QUESTION_ANSWER_BOOK', id=list(chunk))
        log.debug(f'{r} - {r.content}')
