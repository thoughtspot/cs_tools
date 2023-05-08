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

    table.add_column("[b green]Added", justify="center", width=50)
    table.add_column("[b yellow]Modified", justify="center", width=50)
    table.add_column("[b red]Removed", justify="center", width=50)
    return Align.center(table)
