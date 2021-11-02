from typing import List
import json

from typer import Argument as A_, Option as O_
import typer

from cs_tools.helpers.cli_ux import _csv, console, frontend, RichGroup, RichCommand
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig


app = typer.Typer(
    help="""
    Transfer ownership of all objects from one user to another.
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def transfer(
    from_: str=A_(..., metavar='FROM', help='username of the current content owner'),
    to_: str=A_(..., metavar='TO', help='username to transfer content to'),
    tag: List[str]=O_(None, callback=_csv, help='if specified, only move content marked with one or more of these tags'),
    guids: List[str]=O_(None, callback=_csv, help='if specified, only move specific objects'),
    **frontend_kw
):
    """
    Transfer ownership of all objects from one user to another.

    Tags and GUIDs constraints are applied in OR fashion.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    console.print(f'\nTransferring all objects from "{from_}" to "{to_}"')
    ids = set()

    with ThoughtSpot(cfg) as ts:

        if tag is not None or guids is not None:
            r = ts.api._metadata.list(type='USER', pattern=f'%{from_}%')
            r = ts.api._metadata.listas(type='USER', principalid=r.json()['headers'][0]['id'])

            if tag is not None:
                ids.update([_ for _ in r.json()['headers'] if set(_['tags']).intersection(set(tag))])

            if guids is not None:
                ids.update([_ for _ in r.json()['headers'] if _['id'] in guids])

        with console.status('[bold green]running query[/]'):
            try:
                r = ts.api.user.transfer_ownership(
                        fromUserName=from_,
                        toUserName=to_,
                        objectsID=ids
                    )
            except Exception:
                json_msg = r.json()['debug']
                msg = json.loads(json_msg)  # uhm, lol?
                console.print(f'[red]Failed. {msg[-1]}[/]')
            else:
                console.print('[green]Success![/]')
