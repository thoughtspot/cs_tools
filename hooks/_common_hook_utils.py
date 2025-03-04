from __future__ import annotations

import functools as ft

from cs_tools.cli.ux import AsyncTyper

CS_TOOLS_BLOCK_IDENTITY = "~cs~tools"


@ft.cache
def setup_cs_tools_cli() -> AsyncTyper:
    """Fetch the CS Tools CLI."""
    from cs_tools.cli import _monkey  # noqa: F401
    from cs_tools.cli.commands import (
        config as config_command,
        log as log_command,
        self as self_command,
        tools as tools_command,
    )
    from cs_tools.cli.commands.main import app

    tools_command._discover_tools()

    app.add_typer(tools_command.app)
    app.add_typer(config_command.app)
    app.add_typer(self_command.app)
    app.add_typer(log_command.app)

    return app
