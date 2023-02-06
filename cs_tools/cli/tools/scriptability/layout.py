from rich.align import Align
from rich.table import Table
from rich import box


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
        show_footer=True
    )
    table.add_column("Database", justify="center", width=30)         # ~15% of the width
    table.add_column("Schema", justify="center", width=29)           # ~15% of the width
    table.add_column("Table", justify="center", width=55)            # ~30% of width
    table.add_column("Unsynced Columns", justify="right", width=20)  # 4 + length of header
    table.add_column("Whole Table?", justify="center", width=16)     # 4 + length of header
    return Align.center(table)
