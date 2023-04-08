from __future__ import annotations
from dataclasses import dataclass, InitVar
from typing import Callable, List, NewType, Tuple, Union
import contextlib

from rich.console import Console, RenderableType
from rich.align import Align
from rich.table import Table
from rich.live import Live
from rich import box

import datetime as dt


_TaskName = NewType("_TaskName", str)
_TaskDescription = NewType("_TaskDescription", str)


def _default_layout(data: List[WorkTask]) -> Table:
    table = Table(
        width=150,
        box=box.SIMPLE_HEAD,
        row_styles=("dim", ""),
        title_style="white",
        caption_style="white",
        show_footer=True,
    )

    table.add_column("Status", justify="center", width=10)       # 4 + length of title
    table.add_column("Started At", justify="center", width=14)   # 4 + length of title
    table.add_column("Duration (s)", justify="right", width=16)  # 4 + length of title
    table.add_column("Task", width=150 - 10 - 14 - 16, no_wrap=True)

    for row in data:
        table.add_row(*row.values)

    return Align.center(table)


@dataclass
class WorkTask:
    """
    Represents a task to complete.

    Enter the task will start it and initiate a refresh to the parent Live.

    Attributes
    ----------
    name : str

    description : str

    status : str

    started_at : dt.datetime

    duration : int

    """
    name: str
    description: str
    status: str = ":popcorn:"
    _live: InitVar[Live] = None

    def __post_init__(self, rich_live: Live=None):
        self._live = rich_live
        self._total_duration: dt.timedelta = dt.timedelta(seconds=0)
        self._started_at: dt.datetime = None
        self._skipped = False
        self._stopped = False

    @property
    def started_at(self) -> dt.datetime:
        return self._started_at

    @property
    def duration(self) -> dt.timedelta:
        if self._stopped:
            return self._total_duration

        return (dt.datetime.now() - self.started_at) + self._total_duration

    @property
    def values(self) -> Tuple[str]:
        started_at = "" if self.started_at is None else self.started_at.strftime("%H:%M:%S")
        duration = "" if self.started_at is None else f"{self.duration.total_seconds(): >6.2f}"
        return self.status, started_at, duration, self.description

    def skip(self) -> None:
        self._skipped = True
        self.status = None

    def start(self) -> None:
        self.status = ":fire:"
        self._started_at = dt.datetime.now()
        self._stopped = False
        self._live.refresh()

    def stop(self, error: bool = False) -> None:
        if not self._skipped:
            self.status = ":cross_mark:" if error else ":white_heavy_check_mark:"

        self._total_duration += (dt.datetime.now() - self._started_at)
        self._stopped = True
        self._live.refresh()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, trace) -> None:
        self.stop(error=bool(exc))

        if exc is not None:
            raise exc


class LiveTasks(Live):
    """
    A live renderable which can 

    Attributes
    ----------
    work_items: list[WorkItem]

    layout : callable(WorkItems) -> RenderableType

    console : Console

    """

    def __init__(
        self,
        work_items: List[Union[WorkTask, Tuple[_TaskName, _TaskDescription]]],
        layout: Callable[[List[WorkTask]], [RenderableType]] = _default_layout,
        console: Console = None,
    ):
        super().__init__(console=console)
        self.work_items = work_items
        self.layout = layout

    @property
    def work_items(self) -> List[WorkTask]:
        return self._work_items

    @work_items.setter
    def work_items(self, items: List[Union[WorkTask, Tuple[_TaskName, _TaskDescription]]]) -> None:
        if not hasattr(self, "_work_items"):
            self._work_items = []

        for work_item in items:
            if isinstance(work_item, tuple):
                work_item = WorkTask(name=work_item[0], description=work_item[1], _live=self)

            self._work_items.append(work_item)

    def __getitem__(self, task_name: _TaskName) -> WorkTask:
        for work_item in self.work_items:
            if work_item.name == task_name:
                return work_item
        raise KeyError(f"no task found with name '{task_name}'")

    def refresh(self) -> None:
        """
        Draw and refresh the Live.
        """
        with self._lock:
            self._renderable = self.layout(self.work_items)
            super().refresh()
