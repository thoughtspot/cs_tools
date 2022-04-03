import json

from typer import Argument as A_, Option as O_
import typer

from cs_tools.cli.tools.common import setup_thoughtspot
from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT
from cs_tools.cli.ux import CommaSeparatedValuesType, CSToolsGroup, CSToolsCommand, console
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.data.enums import GUID


def _all_user_content(user: GUID, ts: ThoughtSpot):
    """
    Return all content owned by this user.
    """
    types = (
        'QUESTION_ANSWER_BOOK',
        'PINBOARD_ANSWER_BOOK',
        'LOGICAL_TABLE',
        'TAG',
        'DATA_SOURCE'
    )
    content = []

    for metadata_type in types:
        offset = 0

        while True:
            r = ts.api._metadata.list(type=metadata_type, batchsize=500, offset=offset)
            data = r.json()
            offset += len(data)

            for metadata in data['headers']:
                if metadata['author'] == user:
                    metadata['type'] = metadata_type
                    content.append(metadata)

            if data['isLastBatch']:
                break

    return content


app = typer.Typer(
    help="""
    Transfer ownership of all objects from one user to another.
    """,
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def transfer(
    ctx: typer.Context,
    from_: str = A_(..., metavar='FROM', help='username of the current content owner'),
    to_: str = A_(..., metavar='TO', help='username to transfer content to'),
    tag: str = O_(
        None,
        callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
        help='if specified, only move content marked with one or more of these tags'
    ),
    guids: str = O_(
        None,
        callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
        help='if specified, only move specific objects'
    )
):
    """
    Transfer ownership of objects from one user to another.

    Tags and GUIDs constraints are applied in OR fashion.
    """
    ts = ctx.obj.thoughtspot
    ids = set()

    print(tag)
    raise

    if tag is not None or guids is not None:
        with console.status(f'[bold green]Getting all content by: {from_}'):
            user = ts.user.get(from_)
            content = _all_user_content(user=user['id'], ts=ts)

        if tag is not None:
            ids.update([_['id'] for _ in content if set([t['name'] for t in _['tags']]).intersection(set(tag))])

        if guids is not None:
            ids.update([_['id'] for _ in content if _['id'] in guids])

    amt = len(ids) if ids else 'all'

    with console.status(f'[bold green]Transferring {amt} objects from "{from_}" to "{to_}"'):
        try:
            r = ts.api.user.transfer_ownership(
                    fromUserName=from_,
                    toUserName=to_,
                    objectid=ids
                )
        except Exception:
            json_msg = r.json()['debug']
            msg = json.loads(json_msg)  # uhm, lol?
            console.print(f'[red]Failed transferral of objects. {msg[-1]}')
        else:
            console.print(f'[green]Transferred {amt} objects from "{from_}" to "{to_}"')
