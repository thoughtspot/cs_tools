from __future__ import annotations

import pathlib

from cs_tools import __project__
from cs_tools.cli._base import CSTool
from cs_tools.errors import CSToolsError


def get_cs_tool(name: str) -> CSTool:
    """
    Get a CS Tool.

    See the tests for an example.
        tests/programmatic/test_as_ci:test_integration_cli_searchable
    """
    tool_dir = pathlib.Path(__project__.__file__).parent / "cli" / "tools" / name

    if not tool_dir.exists():
        raise CSToolsError(f"no tool registered tool found by name '{name}'")

    return CSTool(directory=tool_dir)
