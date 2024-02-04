from __future__ import annotations

from rich import box
from rich.align import Align
from rich.table import Table as RichTable


class Table(RichTable):
    def __init__(self, data, current_org=None):
        self.data = data
        self.current_org = current_org
        self.live = None

    def __rich_console__(self, console, option):
        table = RichTable(
            title="Searchable Data Gatherer",
            title_style="bold white",
            box=box.SIMPLE_HEAD,
            caption="" if self.current_org is None else f"fetching data in org {self.current_org}",
        )

        table.add_column(header="", width=12, justify="right")

        for column in ("Org", "User", "Group", "Tag", "Object", "Column", "Dependent", "Security"):
            table.add_column(header=column, width=9, justify="center")

        [table.add_row(*row) for row in self.data]
        yield Align.center(table)
