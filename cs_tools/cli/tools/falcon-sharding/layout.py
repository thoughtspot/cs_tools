from typing import Callable, List, Tuple, Union

from rich.console import Console, RenderableType
from rich.align import Align
from rich.table import Table
from rich.live import Live
from rich import box

from cs_tools.types import TMLAPIResponse
from cs_tools import utils

from . import types


def build_table(data: List[TMLAPIResponse]) -> Table:
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

    table.add_column("Status", justify="center", width=10)  # 4 + length of "status"
    table.add_column("Type", justify="center", width=13)    # 4 + length of "liveboard"
    table.add_column("GUID", justify="center", width=40)    # 4 + length of a guid
    table.add_column("Name", width=150 - 10 - 13 - 40, no_wrap=True)
    return Align.center(table)


def build_task_list(data: List[types.WorkItem]) -> Table:
    """
    """
    table = Table(
        width=150,
        box=box.SIMPLE_HEAD,
        row_styles=("dim", ""),
        title_style="white",
        caption_style="white",
        show_footer=True
    )

    table.add_column("Status", justify="center", width=10)       # 4 + length of title
    table.add_column("Started At", justify="center", width=14)   # 4 + length of title
    table.add_column("Duration (s)", justify="right", width=16)  # 4 + length of title
    table.add_column("Task", width=150 - 10 - 14 - 16, no_wrap=True)

    for row in data:
        table.add_row(*row.values)

    return Align.center(table)


class LiveTaskList(Live):
    """
    """

    def __init__(
        self,
        work_items: List[Union[types.WorkItem, Tuple[types.TaskName, types.TaskDescription]]],
        layout: Callable[[], [RenderableType]],
        console: Console
    ):
        super().__init__(console=console)
        self.work_items = work_items
        self.work_layout = layout

    @property
    def work_items(self) -> List[types.WorkItem]:
        return self._work_items

    @work_items.setter
    def work_items(self, items: List[Union[types.WorkItem, Tuple[types.TaskName, types.TaskDescription]]]) -> None:
        if not hasattr(self, "_work_items"):
            self._work_items = []

        for work_item in items:
            if isinstance(work_item, tuple):
                work_item = types.WorkItem(name=work_item[0], description=work_item[1], _live_display=self)

            self._work_items.append(work_item)

        print(self._work_items)

    def __getitem__(self, task_name: types.TaskName) -> types.WorkItem:
        return self.get_task(task_name)

    def get_task(self, task_name: str) -> types.WorkItem:
        return utils.find(lambda w: w.name == task_name, self.work_items)

    def draw(self) -> None:
        with self._lock:
            self._renderable = self.work_layout(self.work_items)

    def refresh(self) -> None:
        self.draw()
        super().refresh()

    def __enter__(self):
        self.draw()
        return super().__enter__()
