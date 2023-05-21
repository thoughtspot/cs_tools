from typing import TextIO
from typing import Any
import functools as ft
import threading
import platform
import time

from rich.console import Console, Renderable
from rich.prompt import Confirm, InvalidResponse
from rich.text import Text


class ConfirmationPrompt(Confirm):

    def __init__(
        self,
        prompt: str = "",
        *,
        console: Console,
        with_prompt: bool = True,
        timeout: float = 60.0,
        **passthru,
    ):
        super().__init__(prompt, console=console, choices=["y", "N"], **passthru)
        self.prompt_suffix = " "
        self.with_prompt = with_prompt
        self.timeout = timeout

    @classmethod
    def ask(
        cls,
        prompt: Renderable = "",
        *,
        with_prompt: bool,
        timeout: float = 60.0,
        default: Any = ...,
        stream: TextIO = None,
        **passthru,
    ):
        """Semantic convenience method around class creation."""
        _prompt = cls(prompt, with_prompt=with_prompt, timeout=timeout, **passthru)
        return _prompt(default=default, stream=stream)

    def process_response(self, value: str) -> bool:
        """Validate that the response is one of [y,N]."""
        value = value.strip().casefold()
        if value not in [choice.casefold() for choice in self.choices]:
            raise InvalidResponse(self.validate_error_message)
        return value == "y"

    def get_input(self, console: Console, prompt: Text, **ignored) -> str:  # noqa: ARG002
        """Take input."""
        console.show_cursor(False)

        if self.with_prompt:
            console.print(prompt)

        event = threading.Event()
        self.response = None
        background_task = ft.partial(self._background_keyboard_input, done_event=event)
        threading.Thread(target=background_task).start()
        event.wait()

        console.show_cursor(True)
        return self.response

    def _background_keyboard_input(self, done_event: threading.Event) -> str:
        """
        This method must be used in a threading.Thread.

        It will take input from stdin, but not display it to the terminal.
        """
        if platform.system() == "Windows":
            import msvcrt
            started_at = time.perf_counter()

            while (time.perf_counter() - started_at) < self.timeout:
                if msvcrt.kbhit():
                    char = msvcrt.getwch()
                    break

                # so we're not crushing the CPU
                time.sleep(0.05)

            else:
                char = "N"

        else:
            import selectors
            import termios
            import sys
            import tty

            SEND_IMMEDIATELY = termios.TCSANOW
            SEND_AFTER_READ  = termios.TCSADRAIN
            old_stdin_parameters = termios.tcgetattr(sys.stdin)

            try:
                # set the parameters associated with the terminal
                tty.setcbreak(sys.stdin, when=SEND_AFTER_READ)
                new_stdin_parameters = termios.tcgetattr(sys.stdin)
                new_stdin_parameters[3] = new_stdin_parameters[3] & ~termios.ECHO
                termios.tcsetattr(sys.stdin, SEND_IMMEDIATELY, new_stdin_parameters)

                # listen for single-key events ... notice .read(1) -> SEND_AND_DISCARD
                s = selectors.DefaultSelector()
                s.register(fileobj=sys.stdin, events=selectors.EVENT_READ)
                events = s.select(timeout=self.timeout)

                if events:
                    selector_key, event = events[0]
                    char = selector_key.fileobj.read(1)
                else:
                    char = "N"

            finally:
                # restore the old sys.stdin
                termios.tcsetattr(sys.stdin, SEND_IMMEDIATELY, old_stdin_parameters)

        self.response = char
        done_event.set()
