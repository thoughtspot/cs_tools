from rich.console import Group
from rich.align import Align
from rich.table import Table
from rich import box

from cs_tools.cli.layout import LiveTasks


def build_table(**table_kwargs) -> Table:
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
        **table_kwargs
    )

    table.add_column("Type", justify="center", width=16)      # 4 + length of "saved answer"
    table.add_column("GUID", justify="center", width=40)      # 4 + length of a GUID
    table.add_column("Modified", justify="center", width=14)  # 4 + length of YYYY-MM-DD
    table.add_column("Author", justify="left", width=20, no_wrap=True)  # ...?
    table.add_column("Name", justify="left", width=150 - (16 + 40 + 14 + 20), no_wrap=True)  # the rest..
    return table


def combined_layout(*, original_layout: Table, new_layout: Table) -> None:

    def _layout(work_items):
        renderable = Group(original_layout(work_items), Align.center(new_layout))
        return renderable

    return _layout
