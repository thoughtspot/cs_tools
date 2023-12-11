from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, NewType, Union
import datetime as dt

from rich import box
from rich.align import Align
from rich.live import Live
from rich.table import Table

if TYPE_CHECKING:
    from rich.console import Console, RenderableType

_TaskName = NewType("_TaskName", str)
_TaskDescription = NewType("_TaskDescription", str)


def _default_layout(data: list[WorkTask]) -> Table:
    table = Table(
        width=150,
        box=box.SIMPLE_HEAD,
        row_styles=("dim", ""),
        title_style="white",
        caption_style="white",
        show_footer=True,
    )

    table.add_column("Status", justify="center", width=10)  # 4 + length of title
    table.add_column("Started At", justify="center", width=14)  # 4 + length of title
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

    def __post_init__(self):
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

        return (dt.datetime.now(tz=dt.timezone.utc) - self.started_at) + self._total_duration

    @property
    def values(self) -> tuple[str]:
        started_at = "" if self.started_at is None else self.started_at.strftime("%H:%M:%S")
        duration = "" if self.started_at is None else f"{self.duration.total_seconds(): >6.2f}"
        return self.status, started_at, duration, self.description

    def skip(self) -> None:
        self._skipped = True
        self.status = None

    def start(self) -> None:
        self.status = ":fire:"
        self._started_at = dt.datetime.now(tz=dt.timezone.utc)
        self._stopped = False

    def stop(self, error: bool = False) -> None:
        if not self._skipped:
            self.status = ":cross_mark:" if error else ":white_heavy_check_mark:"

        self._total_duration += dt.datetime.now(tz=dt.timezone.utc) - self._started_at
        self._stopped = True

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
        work_items: list[Union[WorkTask, tuple[_TaskName, _TaskDescription]]],
        layout: Callable[[list[WorkTask]], [RenderableType]] = _default_layout,
        console: Console = None,
    ):
        super().__init__(console=console)
        self.work_items = work_items
        self.layout = layout

    @property
    def work_items(self) -> list[WorkTask]:
        return self._work_items

    @work_items.setter
    def work_items(self, items: list[Union[WorkTask, tuple[_TaskName, _TaskDescription]]]) -> None:
        if not hasattr(self, "_work_items"):
            self._work_items = []

        for work_item in items:
            if isinstance(work_item, tuple):
                work_item = WorkTask(name=work_item[0], description=work_item[1])

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
