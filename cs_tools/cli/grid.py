from __future__ import annotations

from collections.abc import Collection
from typing import Literal, Optional
import datetime as dt
import itertools as it
import time
import uuid

from rich import box
from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.table import Column, Table

DEFAULT_PROGRESS_INDICATOR = (
    ")======",
    "=)=====",
    "==)====",
    "===)===",
    "====)==",
    "=====)=",
    "======)",
    "======(",
    "=====(=",
    "====(==",
    "===(===",
    "==(====",
    "=(=====",
    "(======",
)


class TableItem:
    """ """

    def __init__(
        self, name: str, *, id: Optional[str] = None, progression: Collection[str] = DEFAULT_PROGRESS_INDICATOR
    ):
        assert all(len(segment) % 2 != 0 for segment in progression)
        self.id = id or uuid.uuid4().hex.upper()[0:6]
        self.name = name
        self.progression = list(progression)
        self.indicator = it.cycle(progression)
        self.started_at: Optional[float] = None
        self._duration: float = 0
        self.state: Literal["NEVER_STARTED", "ACTIVE", "STOPPED", "ERRORED"] = "NEVER_STARTED"

    @property
    def duration(self) -> float:
        if self.state == "NEVER_STARTED":
            return self._duration

        if self.state == "ACTIVE":
            assert self.started_at is not None
            return time.perf_counter() - self.started_at

        return self._duration

    def __rich__(self) -> str:
        if self.state == "NEVER_STARTED":
            return ""

        if self.state == "ERRORED":
            return ":thumbs_down:"

        if self.state == "STOPPED":
            return ":thumbs_up:"

        return next(self.indicator)

    def __enter__(self) -> TableItem:
        self.started_at = time.perf_counter()
        self.state = "ACTIVE"
        return self

    def __exit__(self, exc_type, exc, trace) -> None:
        assert self.started_at is not None
        self._duration = self._duration + (time.perf_counter() - self.started_at)
        self.started_at = None
        self.state = "STOPPED" if exc is None else "ERRORED"


class VerticalProgressTable:
    """ """

    def __init__(self, items: Collection[TableItem], *, justify: str = "CENTER", console=None):
        self.items = items
        self.justify = justify
        self.console = console if console is not None else Console()
        self.started_at: float = 0
        self.live = Live(get_renderable=self.get_renderable, console=self.console)

    def start(self) -> None:
        """Begin the live rendering of this table."""
        self.started_at = time.perf_counter()
        self.live.start()

    def stop(self) -> None:
        """Stop the live rendering of this table."""
        self.live.stop()

    def get_renderable(self) -> RenderableType:
        """Build the renderable."""
        max_width_of_progression = max(len(_) for i in self.items for _ in i.progression)
        progress_table = Table(
            Column(justify="center", width=max(3, max_width_of_progression)),  # PROGRESS INDICATOR
            Column(justify="left"),  # COLUMN NAME
            Column(justify="right", width=len("XXXX.00 s")),  # DURATION INDICATOR
            box=box.SIMPLE_HEAD,
        )

        for row in self.items:
            renderables = (row, row.name, "" if row.state == "NEVER_STARTED" else f"{row.duration:.2f} s")
            progress_table.add_row(*renderables)

        summary_table = Table(
            Column(width=max(3, max_width_of_progression)),
            Column(justify="right"),
            Column(justify="left"),
            box=None,
        )
        summary_table.add_row(
            "", "Total Elapsed", f"{dt.timedelta(seconds=int(time.perf_counter() - self.started_at))}"
        )

        grouped = Group(progress_table, summary_table)
        return Align(grouped, align=self.justify.lower(), width=150)


class HorizontalProgressTable:
    """ """

    def __init__(self, rows: dict[str, Collection[TableItem]], *, justify: str = "CENTER", console=None):
        self.row_width = len(next(iter(rows.values())))
        assert all(len(items) == self.row_width for items in rows.values()), "Row widths should be homogenous"
        self.rows = rows
        self.justify = justify
        self.console = console if console is not None else Console()
        self.started_at: float = 0
        self.live = Live(get_renderable=self.get_renderable, console=self.console)

    def start(self) -> None:
        """Begin the live rendering of this table."""
        self.started_at = time.perf_counter()
        self.live.start()

    def stop(self) -> None:
        """Stop the live rendering of this table."""
        self.live.stop()

    def get_renderable(self) -> RenderableType:
        """Build the renderable."""
        first_row = next(iter(self.rows.values()))
        max_width_of_progression = max(len(_) for i in first_row for _ in i.progression)
        max_width_of_headers = max(len(i.name) for i in first_row)

        progress_table = Table(
            Column(justify="right"),
            *(
                Column(header=item.name, justify="center", width=max(3, max_width_of_headers, max_width_of_progression))
                for item in first_row
            ),
            box=box.SIMPLE_HEAD,
        )

        for row_header, row_values in self.rows.items():
            renderables = (row_header, *row_values)
            progress_table.add_row(*renderables)

        summary_table = Table(
            Column(width=max(3, max_width_of_headers, max_width_of_progression)),
            Column(justify="right"),
            Column(justify="left"),
            box=None,
        )
        summary_table.add_row(
            "", "Total Elapsed", f"{dt.timedelta(seconds=int(time.perf_counter() - self.started_at))}"
        )

        grouped = Group(progress_table, summary_table)
        return Align(grouped, align=self.justify.lower(), width=150)


# if __name__ == "__main__":
#     import random
#     import time

#     console = Console()

#     PROGRESSION = ("😊", "🙂", "😀", "😄", "😆", "😁", "🤪", "🤪")

#     if 1 == 2:
#         tasks = [
#             TableItem(name="Collecting data from [b blue]TS: BI Server", progression=PROGRESSION),
#             TableItem(name="Taking our time to really get things right", progression=PROGRESSION),
#             TableItem(name="Doing the needful", progression=PROGRESSION),
#             TableItem(name="Oh you're still here?", progression=PROGRESSION),
#             TableItem(name="Writing rows to [b blue]CSV Syncer", progression=PROGRESSION),
#         ]

#         table = VerticalProgressTable(items=tasks, console=console)
#         iterable = tasks

#     else:
#         tasks = {  # type: ignore
#             "Org One": [
#                 TableItem(name="A", progression=PROGRESSION),
#                 TableItem(name="BB", progression=PROGRESSION),
#                 TableItem(name="CCC", progression=PROGRESSION),
#                 TableItem(name="DDDD", progression=PROGRESSION),
#                 TableItem(name="EE", progression=PROGRESSION),
#             ],
#             "Org Two": [
#                 TableItem(name="A", progression=PROGRESSION),
#                 TableItem(name="BB", progression=PROGRESSION),
#                 TableItem(name="CCC", progression=PROGRESSION),
#                 TableItem(name="DDDD", progression=PROGRESSION),
#                 TableItem(name="EE", progression=PROGRESSION),
#             ],
#             "Org Three": [
#                 TableItem(name="A", progression=PROGRESSION),
#                 TableItem(name="BB", progression=PROGRESSION),
#                 TableItem(name="CCC", progression=PROGRESSION),
#                 TableItem(name="DDDD", progression=PROGRESSION),
#                 TableItem(name="EE", progression=PROGRESSION),
#             ],
#         }

#         table = HorizontalProgressTable(rows=tasks, console=console)  # type: ignore
#         iterable = (_ for _ in it.chain.from_iterable(tasks.values()))  # type: ignore

#     table.start()

#     for task in iterable:
#         with task:
#             time.sleep(random.randint(1, 5))

#     table.stop()
