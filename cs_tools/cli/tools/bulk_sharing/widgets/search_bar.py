# ruff: noqa: RUF012
from __future__ import annotations

import asyncio

from textual import on
from textual.widgets import Input


class DebouncedInput(Input):
    """An Input widget which debounces change events."""

    def __init__(self, delay: float = 0.5, **input_options) -> None:
        input_options["valid_empty"] = False
        super().__init__(**input_options)
        self.delay = delay
        self._loop = asyncio.get_event_loop()
        self._debounce_timer: asyncio.TimerHandle = None
        self._emitted_tasks: set[asyncio.Task] = set()

    def debounce_timer_is_active(self) -> bool:
        """Determine if the debounce timer is active."""
        if self._debounce_timer is None:
            return False

        if self._debounce_timer.cancelled():
            return False

        return self._debounce_timer.when() > self._loop.time()

    @on(Input.Changed)
    def handle_raw_input_change(self, event: Input.Changed) -> None:
        """Acts as a debounce mechanism."""
        if _has_been_debounced := (event.bubble is False):
            event.bubble = True
            return

        if self.debounce_timer_is_active():
            self._debounce_timer.cancel()

        # PREVENT THE PARENT FROM SEEING Input.Changed THAT HAVE YET TO DEBOUNCE
        event.bubble = False

        self._debounce_timer = self._loop.call_at(self._loop.time() + self.delay, self.fire, event)

    def fire(self, event: Input.Changed) -> None:
        """Emit the latest debounced event."""
        # Re-post the same event. Since it's gotten trhough the debounce time, we'll use
        # the .bubble flag to determine if we should emit it in the listener.
        self.post_message(event)

        # Short-circuit the active timer check.
        self._debounce_timer = None
