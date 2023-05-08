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
    table.add_column("Database", justify="center")
    table.add_column("Schema", justify="center")
    table.add_column("Table", justify="center")
    table.add_column("Column", justify="center", no_wrap=True)
    table.add_column("Internal", justify="center")
    table.add_column("External", justify="center")
    table.add_column("Missing?", justify="center")
    return Align.center(table)
