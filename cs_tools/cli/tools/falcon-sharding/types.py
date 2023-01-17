from dataclasses import dataclass, InitVar
from typing import Tuple
import datetime as dt

from rich.live import Live

TaskName = str  # TODO: underscores or ints only
TaskDescription = str


@dataclass
class WorkItem:
    """Represents a task to complete"""
    name: str
    description: str
    status: str = ":popcorn:"
    started_at: dt.datetime = None
    duration: int = None
    _live_display: InitVar[Live] = None

    def __post_init__(self, rich_live: Live=None):
        self._live_display = rich_live

    def bind_display(self, rich_live: Live):
        self._live_display = rich_live
        return self

    def __enter__(self):
        self.started_at = dt.datetime.now()
        self.status = ":fire:"
        self._live_display.refresh()
        return self

    def __exit__(self, exc_type, exc, trace) -> None:
        self.duration = dt.datetime.now() - self.started_at
        self.status = ":white_heavy_check_mark:" if exc is None else ":cross_mark:"
        self._live_display.refresh()

    @property
    def values(self) -> Tuple[str]:
        started_at = "" if self.started_at is None else self.started_at.strftime("%H:%M:%S")
        duration = "" if self.duration is None else f"{self.duration.total_seconds(): >6.2f}"
        return self.status, started_at, duration, self.description
