# DEV NOTE: @boonhapus, 2023/02/05
#
# This is a temporary fix. Now that CS Tools is a library and be a dependency, we will
# change the tool and syncer implementations such that they can be inherited from and
# properly registered. It's a v1.5.0 task though.
#
from __future__ import annotations

from cs_tools.cli._base import CSTool
from cs_tools.const import TOOLS_DIR
from cs_tools.errors import CSToolsError


def get_cs_tool(name: str) -> CSTool:
    """Get a CS Tool."""
    from cs_tools.cli import _monkey  # noqa: F401

    tool_dir = TOOLS_DIR / name

    if not tool_dir.exists():
        raise CSToolsError(title=f"no tool registered tool found by name '{name}'")

    return CSTool(directory=tool_dir)
