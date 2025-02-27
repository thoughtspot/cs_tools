from __future__ import annotations

from typing import Optional
import asyncio

from cs_tools.cli.keyboard import keys
from cs_tools.cli.keyboard.keyboard import KeyboardListener, KeyPressContext


class ConfirmationListener(KeyboardListener):
    """A small utility which listens to Y/N answers."""

    def __init__(self, timeout: float):
        super().__init__()
        self.timeout = timeout
        self._timer_task: Optional[asyncio.Task] = None
        self.response: Optional[str] = None

        for character in "YyNn":
            self.bind(keys.Key.letter(character), fn=self.set_result)

    async def set_result(self, ctx: KeyPressContext) -> None:
        """Set the response and immediately terminate."""
        self.response = ctx.key.data
        await self.stop()

    async def timer(self) -> None:
        """Background timer."""
        try:
            await asyncio.sleep(self.timeout)

        # If we get cancelled before reaching timeout, nothing needs to happen.
        except asyncio.CancelledError:
            pass

        # If we hit the timeout, stop the background key loop.
        else:
            await self.stop()

    async def start(self, **passthru) -> None:
        """Start a timer and kick off the background key loop."""
        self._timer_task = asyncio.create_task(self.timer())
        await super().start(**passthru)

    async def stop(self, **passthru) -> None:
        """Ensure the timer gets cancelled."""
        assert self._timer_task is not None, "ConfirmationListener has not yet been started"
        self._timer_task.cancel()
        await super().stop(**passthru)

        if self.response is None:
            self.response = "N"
