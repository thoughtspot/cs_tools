from __future__ import annotations

import logging
import pathlib
import shutil

from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper
from cs_tools.updater import cs_tools_venv
import typer

log = logging.getLogger(__name__)
app = AsyncTyper(name="logs", hidden=True)


@app.command()
def report(
    save_path: pathlib.Path = typer.Argument(
        None,
        help="location on disk to save logs to",
        metavar="DIRECTORY",
        file_okay=False,
        resolve_path=True,
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
    RICH_CONSOLE.print(f"\nSaving logs to [b blue link={save_path.resolve().as_posix()}]{save_path.resolve()}[/]\n")

    logs_dir = cs_tools_venv.subdir(".logs")
    sorted_newest = sorted(logs_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)

    for i, logfile in enumerate(sorted_newest, start=1):
        if i <= latest:
            RICH_CONSOLE.print(f"  [fg-secondary]{logfile.name}")
            shutil.copy(logfile, save_path)
