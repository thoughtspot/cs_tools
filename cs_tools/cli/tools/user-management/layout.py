from __future__ import annotations

from rich import box
from rich.align import Align
from rich.table import Table


def build_table() -> Table:
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

    table.add_column("[fg-success]Added", justify="center", width=50)
    table.add_column("[fg-warn]Modified", justify="center", width=50)
    table.add_column("[fg-error]Removed", justify="center", width=50)
    return Align.center(table)
