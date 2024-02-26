from __future__ import annotations

import pathlib

from cs_tools import __project__
from cs_tools.cli.ux import CSToolsGroup
from cs_tools.programmatic import get_cs_tool
from cs_tools.settings import _meta_config as meta
import typer

app = typer.Typer(
    cls=CSToolsGroup,
    name="tools",
    help="""
    Run an installed tool.

    Tools are a collection of scripts to perform different functions
    which aren't native to ThoughtSpot or advanced functionality for
    clients who have a well-adopted platform.
    """,
    subcommand_metavar="<tool>",
    invoke_without_command=True,
    epilog=(
        f":wrench: [cyan][link={__project__.__docs__}/tools]Documentation[/] "
        f":bug: [link={__project__.__bugs__}]Found a bug?[/] "
        f":megaphone: [link={__project__.__help__}]Feedback[/][/] "
        + (
            f":computer_disk: [green]{meta.default_config_name}[/] (default)"
            if meta.default_config_name is not None
            else ""
        )
    ),
)

for path in pathlib.Path(__file__).resolve().parent.parent.joinpath("tools").iterdir():
    if path.name == "__pycache__" or not path.is_dir():
        continue

    tool = get_cs_tool(path.name)

    if tool.privacy == "unknown":
        continue

    # add tool to the cli
    app.add_typer(
        tool.app,
        name=tool.name,
        rich_help_panel=tool.app.rich_help_panel,
        hidden=tool.privacy != "public",
    )
