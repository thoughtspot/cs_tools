import pathlib
import shutil

from typer import Argument as A_, Option as O_
import typer

from cs_tools.cli.ux import CSToolsGroup, CSToolsCommand
from cs_tools.const import APP_DIR


app = typer.Typer(
    cls=CSToolsGroup,
    name='logs',
    help="""
    Export and view log files.

    Something went wrong? Log files will help the ThoughtSpot team understand
    how to debug and fix it.
    """
)


@app.command(cls=CSToolsCommand)
def export(
    save_path: pathlib.Path = A_(
        ...,
        help='location on disk to save logs to',
        metavar='DIRECTORY',
        file_okay=False,
        resolve_path=True
    ),
):
    """
    Grab logs to share with ThoughtSpot.
    """
    save_path.mkdir(parents=True, exist_ok=True)
    log_dir = APP_DIR / 'logs'

    for log in log_dir.iterdir():
        shutil.copy(log, save_path)
