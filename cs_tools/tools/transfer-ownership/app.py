import json

from typer import Argument as A_, Option as O_
import typer

from cs_tools.helpers.cli_ux import console, show_tool_options, frontend
from cs_tools.settings import TSConfig
from cs_tools.api import ThoughtSpot


app = typer.Typer(
    help="""
    Transfer ownership of all objects from one user to another.
    """,
    callback=show_tool_options,
    invoke_without_command=True
)


@app.command()
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

    with ThoughtSpot(cfg) as api:
        console.print(f'\nTransferring all objects from "{from_}" to "{to_}"')

        with console.status('[bold green]running query[/]'):
            r = api.user.transfer_ownership(from_, to_)

        try:
            r.raise_for_status()
            console.print('[green]Success![/]')
        except Exception:
            json_msg = r.json()['debug']
            msg = json.loads(json_msg)  # uhm, lol?
            console.print(f'[red]Failed. {msg[-1]}[/]')
