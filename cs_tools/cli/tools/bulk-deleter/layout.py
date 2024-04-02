from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.align import Align
from rich.table import Table

if TYPE_CHECKING:
    from . import types


def build_table(data: list[types.DeleteRecord]) -> Table:
    """
    Layout for the UI.
    """
    table = Table(
        width=150,
        box=box.SIMPLE_HEAD,
        row_styles=("dim", ""),
        title_style="white",
        caption_style="white",
        show_footer=True,
    )

    table.add_column("Status", justify="center", width=10)  # 4 + length of "status"
    table.add_column("Type", justify="center", width=13)  # 4 + length of "liveboard"
    table.add_column("GUID", justify="center", width=40)  # 4 + length of a guid
    table.add_column("Name", width=150 - 10 - 13 - 40, no_wrap=True)

    for row in data:
        table.add_row(*row.values)

    return Align.center(table)
