from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, TextIO, Union
import functools as ft
import platform
import queue
import threading
import time

from rich.prompt import Confirm, InvalidResponse
import pydantic

from cs_tools._compat import Self
from cs_tools.datastructures import _GlobalModel

if TYPE_CHECKING:
    from rich.console import Console, RenderableType
    from rich.text import Text

IS_WINDOWS = platform.system() == "Windows"


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
        prompt: RenderableType = "",
        *,
        with_prompt: bool,
        timeout: float = 60.0,
        default: Any = ...,
        stream: Optional[TextIO] = None,
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

    def get_input(self, console: Console, prompt: Text, *args, **kwargs) -> str:  # noqa: ARG002
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
            import sys
            import termios
            import tty

            SEND_IMMEDIATELY = termios.TCSANOW
            SEND_AFTER_READ = termios.TCSADRAIN
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


class Key(_GlobalModel):
    """Represents a key pressed on the keyboard."""

    key: bytes

    @pydantic.computed_field  # type: ignore[misc]
    @property
    def character(self) -> Optional[str]:
        return self.key.decode() if len(self.key) == 1 else None

    @pydantic.computed_field  # type: ignore[misc]
    @property
    def name(self) -> Optional[str]:
        # Technically, we know a lot more.
        # https://github.com/Textualize/textual/blob/244e42c6fcfd4989de08c57ffc10db1e5fc87add/src/textual/_ansi_sequences.py#L8
        known_ansi_sequences = {
            b" ": "Space",
            b"\r": "Enter",
            b"\x08": "Backspace",
            b"\x1b": "Escape",
            b"\xe0H": "Up",
            b"\xe0P": "Down",
            b"\xe0K": "Left",
            b"\xe0M": "Right",
        }

        return known_ansi_sequences.get(self.key, self.character if self.is_printable else "Unknown")

    @property
    def is_printable(self) -> bool:
        """Determines if the produces a unicode character."""
        return False if self.character is None else self.character.isprintable()

    def __eq__(self, other: Union[Key, str]) -> bool:  # type: ignore[override]
        if isinstance(other, Key):
            return self.key.upper() == other.key.upper()

        character = self.character or repr(self.key)
        return character.upper() == str(other).upper()

    def __str__(self) -> str:
        key_repr = self.character or repr(self.key)[2:-1]

        if self.key in (b"\x1b", b"\r"):  # Escape, Enter
            key_repr = f"{key_repr!r}"[1:-1]

        return f"<Key: {self.name} ({key_repr})>"


class Keys:
    SPACE = Key(key=b" ")
    ENTER = RETURN = Key(key=b"\r")
    BACKSPACE = Key(key=b"\x08")
    ESC = ESCAPE = Key(key=b"\x1b")
    UP = Key(key=b"\xe0H")
    DOWN = Key(key=b"\xe0P")
    LEFT = Key(key=b"\xe0K")
    RIGHT = Key(key=b"\xe0M")

    @staticmethod
    @ft.cache
    def char(value: Any) -> Key:
        """Convert a single character into a Key"""
        if len(str(value)) > 1:
            raise ValueError(f"You must only provide single characters, got '{value}'")
        return Key(key=str(value).encode())


class KeyboardListener:
    """ """

    def __init__(self, *, console: Console, whitelist: Optional[list[Key]] = None):
        self.console = console
        self.whitelist = whitelist
        self.should_stop = False
        self._bg_thread = threading.Thread(target=self._windows_listener if IS_WINDOWS else self._termios_listener)
        self.queue: queue.Queue[Key] = queue.Queue()

    @property
    def is_running(self) -> bool:
        """Determine if the background thread is running."""
        return not self.should_stop

    def _windows_listener(self) -> None:
        """Listen for keys on Windows."""
        # TODO: REPLACE IMPL WITH TEXTUALIZE'S LISTENER ?
        # https://github.com/Textualize/textual/blob/244e42c6fcfd4989de08c57ffc10db1e5fc87add/src/textual/drivers/win32.py#L246-L273
        import msvcrt

        KEY_PRESS_WAITING = msvcrt.kbhit
        GET_KEY_VALUE = msvcrt.getch

        while not self.should_stop:
            if not KEY_PRESS_WAITING():
                time.sleep(0.01)
                continue

            key_press = GET_KEY_VALUE()

            if key_press in (b"\000", b"\xe0"):
                key_press += GET_KEY_VALUE()

            key = Key(key=key_press)

            if self.whitelist is not None and key not in self.whitelist:
                continue

            self.queue.put(key)

    def _termios_listener(self) -> None:
        """Listen for keys on Mac, Linux."""
        # TODO: REPLACE IMPL WITH TEXTUALIZE'S LISTENER ?
        # https://github.com/Textualize/textual/blob/244e42c6fcfd4989de08c57ffc10db1e5fc87add/src/textual/drivers/linux_driver.py#L251-L283
        import selectors
        import sys
        import termios
        import tty

        SEND_IMMEDIATELY = termios.TCSANOW
        SEND_AFTER_READ = termios.TCSADRAIN
        old_stdin_parameters = termios.tcgetattr(sys.stdin)

        # set the parameters associated with the terminal
        tty.setcbreak(sys.stdin, when=SEND_AFTER_READ)
        new_stdin_parameters = termios.tcgetattr(sys.stdin)
        new_stdin_parameters[3] = new_stdin_parameters[3] & ~termios.ECHO
        termios.tcsetattr(sys.stdin, SEND_IMMEDIATELY, new_stdin_parameters)

        # listen for single-key events .read(1)
        s = selectors.DefaultSelector()
        s.register(fileobj=sys.stdin, events=selectors.EVENT_READ)

        try:
            while not self.should_stop:
                if selector_events := s.select(timeout=0.01):
                    selector_key, event = selector_events[0]
                    key_press = selector_key.fileobj.read(1)

                    key = Key(key=key_press)

                    if self.whitelist is not None and key not in self.whitelist:
                        continue

                    self.queue.put(key_press)
        finally:
            # restore the old sys.stdin
            termios.tcsetattr(sys.stdin, SEND_IMMEDIATELY, old_stdin_parameters)

    def start(self) -> None:
        """Tell the background thread to start."""
        self._bg_thread.start()

    def stop(self) -> None:
        """Tell the background thread to stop."""
        self.should_stop = True

    def get(self) -> Key:
        """Fetch the next Key."""
        return self.queue.get()

    def simulate(self, key: Key) -> None:
        """Simulate a key press."""
        self.queue.put(key)

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, class_, exception, traceback) -> bool:
        self.should_stop = True


if __name__ == "__main__":
    from rich.console import Console

    console = Console()

    # fmt: off
    console.print(
        "\n"
        "[b blue]Press any key..[/]"
        "\n[dim]CTRL + C to exit"
        "\n"
    )
    # fmt: on

    with KeyboardListener(console=console) as kb:
        while kb.is_running:

            try:
                key = kb.get()
            except KeyboardInterrupt:
                kb.stop()
                continue

            if key == Key(key=b"\x11"):
                kb.stop()

            console.print(key)

    console.print()
