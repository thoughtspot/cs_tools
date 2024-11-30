from __future__ import annotations

from math import inf as INFINITY
from typing import Callable, Self, cast
import asyncio
import datetime as dt
import logging
import time

from rich import box, live, panel
from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.progress import BarColumn, Task, TimeElapsedColumn
from rich.table import Column, Table

from cs_tools import utils
from cs_tools.cli.ux import RICH_CONSOLE

log = logging.getLogger(__name__)


class WorkTask:
    """Store information about a task."""

    # DEV NOTE: @boonhapus, 10/19/2024
    #
    # This is a custom minimal implementation of rich.progress.Task because the original
    # is a python dataclass, which are difficult to inherit and extend from.
    #
    # Not all properties or methods are re-implemented.
    #
    # Further reading:
    # https://github.com/Textualize/rich/blob/0f2f51b872d14588de3a65968f5cdde6fb5694a3/rich/progress.py#L937-L1060
    #

    def __init__(
        self, id: str, description: str, total: float | None = None, completed: float = 0, visible: bool = True
    ):
        self.id = id
        self.description = description
        self.total = total
        self.completed = completed
        self.visible = visible
        self.get_time = time.perf_counter
        self.start_time: float | None = None
        self.stop_time: float | None = None
        self.finished_time: float | None = None

        self._previously_elapsed: float = 0
        self._prog_bar = BarColumn()
        self._prog_elasped = TimeElapsedColumn()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if task_is_skipped := (self.start_time is None):
            return

        self.stop()

    @property
    def started(self) -> bool:
        """Check if the task as started."""
        return self.start_time is not None

    @property
    def elapsed(self) -> float | None:
        """Time elapsed since task was started, or ``None`` if the task hasn't started."""
        if self.start_time is None:
            return None
        if self.stop_time is not None:
            return (self.stop_time - self.start_time) + self._previously_elapsed
        return (self.get_time() - self.start_time) + self._previously_elapsed

    @property
    def finished(self) -> bool:
        """Check if the task has finished."""
        return self.finished_time is not None

    @property
    def percentage(self) -> float:
        """Get progress of task as a percentage. If a None total was set, returns 0."""
        if not self.total:
            return 0.0
        completed = (self.completed / self.total) * 100.0
        completed = min(100.0, max(0.0, completed))
        return completed

    def start(self, total: float | None = INFINITY) -> None:
        """Start the task."""
        if self.started:
            self._previously_elapsed += (self.stop_time or self.get_time()) - self.start_time
            self.total = None if self.total == -1 else self.total
            self.stop_time = None
            self.finished_time = None

        self.start_time = self.get_time()

        if total is not INFINITY:
            self.total = total

    def stop(self) -> None:
        """Stop the task."""
        self.stop_time = self.get_time()
        self.total = -1 if self.total is None else self.total
    
    def skip(self) -> None:
        """Skip the task."""
        self.start_time = None

    def advance(self, step: float) -> None:
        """Advance the task by the step value."""
        if self.total is None:
            log.warning("Indefinite progress bars do not support advancing their .completed values.")
            return

        if not self.started:
            self.start()

        self.completed += step

        if self.completed >= self.total and self.finished_time is None:
            self.finished_time = self.elapsed

    def final(self) -> None:
        """Mark the task as finished."""
        self.stop()
        self.finished_time = self.elapsed

    def __render__(self, text_width: int, bar_width: int) -> RenderableType:
        """Generate a row in the WorkTracker."""
        table = Table(
            Column(width=text_width, no_wrap=True),
            Column(width=bar_width, no_wrap=True),
            Column(width=len("HHHmMMmSSs"), no_wrap=True),
            padding=(0, 1),
            box=None,
            show_header=False,
        )

        self._prog_bar.bar_width = bar_width

        table.add_row(
            self.description,
            self._prog_bar(cast(Task, self)) if self.started else "--",
            self._prog_elasped(cast(Task, self)),
        )

        return table


class WorkTracker(live.Live):
    """Present information about concurrent running tasks."""

    def __init__(
        self,
        title: str,
        *,
        tasks: list[WorkTask],
        verbose: bool = True,
        console: Console = RICH_CONSOLE,
        extra_renderable: Callable[[], RenderableType] | None = None,
    ) -> None:
        self.title = title
        self.tasks = tasks
        self.verbose = verbose
        self._loop = utils.get_event_loop()
        self._started_at: dt.datetime | None = None
        self.max_width = 125
        self.extra_renderable = extra_renderable
        super().__init__(console=console, refresh_per_second=3, get_renderable=self.generate_tracker)

    def __getitem__(self, key: str) -> WorkTask:
        try:
            return next(t for t in self.tasks if t.id.casefold() == key.casefold())
        except StopIteration:
            raise KeyError(f"WorkTracker has no task '{key}'") from None

    def generate_tracker(self) -> RenderableType:
        """
        Generate a live report.

        It generally looks like the following..

            ────────────────────────────────────────────────────────────────────────────────────────────────────────────
                                                                { self.title }                                         
            ────────────────────────────────────────────────────────────────────────────────────────────────────────────
            Task name  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  0:00:00
            Task name  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  0:00:00
            Task name  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╸       0:00:00
            Task name  ━━━━━━━━━━━━━━━━━━━━━━━━━━━╸                                                              0:00:00
            Task name  ━                                                                                         0:00:00
            Task name  --                                                                                        -:--:--
            Task name  --                                                                                        -:--:--
            ────────────────────────────────────────────────────────────────────────────────────────────────────────────
            Elapsed   0h 00m 01s                                                                                        
            ────────────────────────────────────────────────────────────────────────────────────────────────────────────
        """
        NOWTIME = dt.datetime.now(tz=dt.timezone.utc)
        ELAPSED = NOWTIME - (self._started_at or NOWTIME)

        header = panel.Panel(
            renderable=Align.center(self.title),
            width=self.max_width,
            box=box.HORIZONTALS,
            border_style="bg-primary",
        )

        task_table = Table(width=self.max_width, box=None, show_header=False)
        task_table.add_column()

        title_width = max(len(self.console.render_str(task.description, highlight=False)) for task in self.tasks) + 3
        bar_width = self.max_width - title_width - 10

        for task in self.tasks:
            task_table.add_row(task.__render__(text_width=title_width, bar_width=bar_width))

        footer = Table(width=self.max_width, box=box.HORIZONTALS, show_header=False, border_style="bg-primary")
        footer.add_column(justify="left")
        footer.add_column(justify="center")
        footer.add_column(justify="right")

        footer.add_row(
            f"[fg-primary]Elapsed[/] {utils.timedelta_strftime(ELAPSED)}",
            "",
            f"[bg-primary]{len(asyncio.all_tasks(loop=self._loop)):,} Background Tasks" if self.verbose else "",
        )

        xtra = self.extra_renderable() if self.extra_renderable is not None else ""

        return Align.center(Group(header, task_table, footer, xtra))

    def __enter__(self) -> WorkTracker:
        self._started_at = dt.datetime.now(tz=dt.timezone.utc)
        self.start(refresh=self._renderable is not None)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.refresh()
