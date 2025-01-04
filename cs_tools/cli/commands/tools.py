from __future__ import annotations

from cs_tools import __project__, programmatic, utils
from cs_tools.cli.ux import AsyncTyper
from cs_tools.settings import _meta_config as meta

app = AsyncTyper(
    name="tools",
    help="""
    Run an installed tool.

    Tools are a collection of scripts to perform different functions
    which aren't native to ThoughtSpot or advanced functionality for
    clients who have a well-adopted platform.
    """,
    subcommand_metavar="<tool>",
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


def _discover_tools() -> None:
    """Find and add the built-in tools."""
    CS_TOOLS_PKG_DIR = utils.get_package_directory("cs_tools")

    for path in (CS_TOOLS_PKG_DIR / "cli" / "tools").iterdir():
        if path.name == "__pycache__" or not path.is_dir():
            continue

        # if path.name not in ("searchable", "archiver", "bulk-deleter", "bulk_sharing", "extractor", "rtql"):
        if path.name not in ("rtql", "searchable"):
            continue

        tool_info = programmatic.CSToolInfo(directory=path)

        if tool_info.privacy == "unknown":
            continue

        # add tool to the cli
        app.add_typer(
            tool_info.app,
            name=tool_info.name,
            rich_help_panel=tool_info.app.rich_help_panel,
            hidden=not (tool_info.privacy == "public"),
        )
