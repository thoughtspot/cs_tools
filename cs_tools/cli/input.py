from typing import TextIO
import platform
import time

from rich.console import Console
from rich.prompt import Confirm, InvalidResponse
from rich.panel import Panel
from rich.text import Text

class ConfirmationPrompt(Confirm):

    def __init__(self, prompt: str = "", *, console: Console, with_prompt: bool = True, timeout: float = 60.0, **kw):
        super().__init__(prompt, console=console, choices=["y", "N"])
        self.prompt_suffix = " "
        self.with_prompt = with_prompt
        self.timeout = timeout

    @classmethod
    def ask(cls, *a, default = ..., stream = None, **kw):
        _prompt = cls(*a, **kw)
        return _prompt(default=default, stream=stream)

    # def make_prompt(self, default) -> Text:
    #     """ """
    #     if not self.with_prompt or default == ...:
    #         return Text("")
    #     return Panel.fit(Text.from_markup(default))

    def process_response(self, value: str) -> bool:
        value = value.strip().casefold()
        if value not in [choice.casefold() for choice in self.choices]:
            raise InvalidResponse(self.validate_error_message)
        return value == "y"

    def get_input(self, console: Console, prompt: Text, password: bool, stream: TextIO=None) -> str:
        """ """
        console.show_cursor(False)
        console.print(prompt, end="")
        response = self._background_keyboard_input()
        console.show_cursor(True)
        return response

    def _background_keyboard_input(self) -> str:
        """ """

        if platform.system() == "Windows":
            import msvcrt
            started_at = time.perf_counter()

            while (time.perf_counter() - started_at) < self.timeout:
                if msvcrt.kbhit():
                    char = msvcrt.getwch()
                    break
            else:
                char = "N"

        else:
            import selectors
            import termios
            import sys

            s = selectors.DefaultSelector()
            s.register(fileobj=sys.stdin.fileno(), events=selectors.EVENT_READ)
            events = s.select(timeout=self.timeout)

            if events:
                selector_key, event = events[0]
                char = selector_key.fileobj.readline().strip()
            else:
                termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)

        # else:
        #     import termios
        #     import sys
        #     import tty

        #     fd = sys.stdin.fileno()
        #     old_stdin = termios.tcgetattr(fd)

        #     try:
        #         # https://manpages.debian.org/bullseye/manpages-dev/termios.3.en.html
        #         tty.setraw(fd)
        #         new_stdin = termios.tcgetattr(fd)
        #         new_stdin[3] = new_stdin[3] & ~termios.ECHO
        #         termios.tcsetattr(fd, termios.TCSADRAIN, new_stdin)
        #         char = input("")

        #     finally:
        #         char = "N"
        #         termios.tcsetattr(fd, termios.TCSADRAIN, old_stdin)

        print(f"GOT: {char}")
        return char


if __name__ == "__main__":
    console = Console()
    response = ConfirmationPrompt.ask(prompt="Continue", console=console, timeout=1)
    print(response)
