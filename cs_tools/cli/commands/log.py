from __future__ import annotations

import functools as ft
import pathlib
import shutil

from cs_tools import _types
from cs_tools.cli import custom_types
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper
from cs_tools.updater import cs_tools_venv
import typer

app = AsyncTyper(name="logs", help="Grab logs to share with ThoughtSpot.")


@app.command()
def report(
    save_path: pathlib.Path = typer.Argument(
        ...,
        metavar="DIRECTORY",
        help="Where to export the logs.",
        click_type=custom_types.Directory(exists=False, make=True),
    ),
    latest: int = typer.Option(1, help="Number of most recent logfiles to export.", min=1),
) -> _types.ExitCode:
    """Grab logs to share with ThoughtSpot."""
    RICH_CONSOLE.print(f"\nDirectory :link: [fg-secondary][link={save_path.as_posix()}]{save_path}\n")
    LAST_MODIFIED = ft.partial(lambda path: path.stat().st_mtime)
    LOGS_DIRECTORY = cs_tools_venv.subdir(".logs")

    for idx, logfile in enumerate(sorted(LOGS_DIRECTORY.iterdir(), key=LAST_MODIFIED, reverse=True), start=1):
        if idx <= latest:
            stats = logfile.stat()

            RICH_CONSOLE.print(f"  Copying [fg-secondary]{logfile.name}[/] {stats.st_size / 1024:>10,.2f} KB")
            shutil.copy(logfile, save_path)

    RICH_CONSOLE.print("\n")
    return 0
