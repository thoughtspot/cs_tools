from dataclasses import dataclass, field
from typing import Dict, List
import logging
import asyncio

from horde.events import HordeInit, SpawnZombie, DespawnStart, HordeStop
from rich.console import Console, RenderableType
from rich.layout import Layout
from rich.align import Align
from rich.style import Style
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from pynput import keyboard
from rich import box
from horde._ui import UI
import horde

from . import zombie

log = logging.getLogger(__name__)


@dataclass
class ZombieDataRow:
    zombie: zombie.ThoughtSpotZombie
    zombie_data: List[zombie.ThoughtSpotPerformanceEvent] = field(default_factory=list)

    def generate_row_data(self) -> List[str]:
        data = [
            self.zombie.state.value.title()
        ]
        return data


class SwarmUI(UI):
    """
    """

    def __init__(self, environment):
        super().__init__(environment=environment)
        self._display: Live = None
        self._data: Dict[int, ZombieDataRow] = {}
        self.hotkeys = {
            "q": self._handle_quit,
            # "+": self._handle_show_more_zombies,
            # "-": self._handle_show_less_zombies,
        }

    @property
    def horde_state(self) -> str:
        return self.horde.runner.state.value.upper()

    def display_refresh(self) -> None:
        """
        Draw and refresh the Live.
        """
        with self._display._lock:
            self._display._renderable = self.layout()

        self._display.refresh()

    def _handle_quit(self) -> None:
        self.horde._loop.create_task(self.horde.runner.stop())

    #
    #
    #

    def add_row(self, event: horde.events.SpawnZombie) -> None:
        self._data[event.zombie.zombie_id] = ZombieDataRow(zombie=event.zombie)

    def add_data_to_row(self, event: zombie.ThoughtSpotPerformanceEvent) -> None:
        self._data[event.zombie.zombie_id].data.append(event)

    def layout(self) -> RenderableType:
        """Draw the layout."""
        layout = Layout()

        # GENERATE FORMAT
        layout.split(
            Layout(name="header", size=3),
            Layout(name="table"),
        )

        # GENERATE CONTROLS
        controls = Table.grid(padding=3)
        controls.add_column(justify="right")
        controls.add_row("[bold blue]Q[/] Quit")

        # GENERATE HEADER
        header = Table.grid(expand=True)
        header.add_column(justify="left")
        header.add_column(justify="center", ratio=1)
        header.add_column(justify="right")
        header.add_row(
            f"runtime [b blue]{self.horde.runtime}[/]",
            ":bug: Join the [b]Swarm[/]!",
            controls,
        )

        # GENERATE DATA TABLE
        table = Table(
            caption=f"Current State: {self.horde.runner.state.value.upper()}",
            box=box.SIMPLE_HEAD,
            show_footer=True,
            row_styles=["dim", ""],
            title_style="white",
            caption_style="white",
            width=150,
        )

        # FILL THE TABLE WITH DATA
        for idx, (zombie_id, zombie_data_row) in enumerate(self._data.items(), start=1):
            if idx >= 25:
                break

            table.add_row(*zombie_data_row.generate_row_data())

        # FILL THE TABLE FOOTER
        # EMTPY_ROW = [""] * len(table.columns)
        # table.add_row(*EMTPY_ROW)
        # table.columns[4].footer = rich_cast(sum(total["requests"]))
        # table.columns[5].footer = rich_cast(sum(total["errors"]))
        # table.columns[6].footer = rich_cast(mean(total["average_latency_s"])) if total["average_latency_s"] else ""
        # table.columns[7].footer = rich_cast(mean(total["error_rate"])) if total["error_rate"] else ""

        layout["header"].update(Panel(header, style="white"))
        layout["table"].update(Align.center(table))
        return layout

    #
    #
    #

    async def background_tick(self) -> None:
        """Update the UI."""
        while True:
            await asyncio.sleep(0.25)
            self.display_refresh()

    async def start(self, *, clear_on_exit: bool = False, console: Console = Console(), **runner_kwargs) -> int:
        """
        Start the animation.
        """
        if console.size.width <= 150:
            log.warning("Terminal is not wide enough to properly fit the display, please maximize and run again")
            log.info(f" Current width: {console.size.width: >4}")
            log.info(f"Required width:  150")
            return 1

        kb_listener = keyboard.GlobalHotKeys(self.hotkeys)
        kb_listener.start()

        with Live(console=console) as display:
            self._display = display

            self.horde.events.add_listener(HordeInit, listener=lambda evt: self.display_refresh())
            self.horde.events.add_listener(SpawnZombie, listener=self.add_row)
            self.horde.events.add_listener(zombie.ThoughtSpotPerformanceEvent, listener=self.add_data_to_row)
            self.horde.events.add_listener(DespawnStart, listener=lambda evt: self.display_refresh())
            self.horde.events.add_listener(HordeStop, listener=lambda evt: self.display_refresh())

            bg_task = asyncio.create_task(self.background_tick())
            await self.horde.runner.start(**runner_kwargs)
            await self.horde.runner.join()
            bg_task.cancel()
            await asyncio.sleep(0.0)
            self.display_refresh()

        kb_listener.stop()

        if clear_on_exit:
            console.clear()

        return 0
