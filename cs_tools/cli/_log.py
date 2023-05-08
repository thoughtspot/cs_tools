import pathlib
import shutil

import typer


from cs_tools.cli.ux import CSToolsCommand

from cs_tools.cli.ux import CSToolsGroup
from cs_tools.cli.ux import rich_console
from cs_tools.const import APP_DIR

app = typer.Typer(cls=CSToolsGroup, name="logs", hidden=True)


@app.command(cls=CSToolsCommand)
def report(
    save_path: pathlib.Path = typer.Argument(
        None, help="location on disk to save logs to", metavar="DIRECTORY", file_okay=False, resolve_path=True,
    ),
    latest: int = typer.Option(1, help="number of most recent logfiles to export", min=1),
):
    """
    Grab logs to share with ThoughtSpot.
    """
    while save_path is None:
        save_fp = typer.prompt(f"Where should we save the last {latest} log files to?")
        save_path = pathlib.Path(save_fp)

    save_path.mkdir(parents=True, exist_ok=True)
    rich_console.print(f"\nSaving logs to [b blue link={save_path.resolve().as_posix()}]{save_path.resolve()}[/]\n")

    sorted_newest = sorted(APP_DIR.joinpath("logs").iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)

    for i, log in enumerate(sorted_newest, start=1):
        if i <= latest:
            rich_console.print(f"  [b blue]{log.name}")
            shutil.copy(log, save_path)
