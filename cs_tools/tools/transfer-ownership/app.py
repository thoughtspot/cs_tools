import json

from typer import Argument as A_, Option as O_
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.settings import TSConfig
from cs_tools.thoughtspot import ThoughtSpot


app = typer.Typer(
    help="""
    Transfer ownership of all objects from one user to another.
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def transfer(
    from_: str=O_(..., '--from', help='username of the current content owner'),
    to_: str=O_(..., '--to', help='username to transfer content to'),
    **frontend_kw
):
    """
    Transfer ownership of all objects from one user to another.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as ts:
        console.print(f'\nTransferring all objects from "{from_}" to "{to_}"')

        with console.status('[bold green]running query[/]'):
            r = ts.api.user.transfer_ownership(from_, to_)

        try:
            r.raise_for_status()
            console.print('[green]Success![/]')
        except Exception:
            json_msg = r.json()['debug']
            msg = json.loads(json_msg)  # uhm, lol?
            console.print(f'[red]Failed. {msg[-1]}[/]')
