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
            import tty

            old_stdin_parameters = termios.tcgetattr(sys.stdin)

            try:
                # https://manpages.debian.org/bullseye/manpages-dev/termios.3.en.html
                tty.setraw(sys.stdin)
                new_stdin_parameters = termios.tcgetattr(sys.stdin)
                new_stdin_parameters[3] = new_stdin_parameters[3] & ~termios.ECHO

                # set the parameters associated with the terminal
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new_stdin_parameters)

                s = selectors.DefaultSelector()
                s.register(fileobj=sys.stdin, events=selectors.EVENT_READ)
                events = s.select(timeout=self.timeout)

                if events:
                    selector_key, event = events[0]
                    char = selector_key.fileobj.read(1)
                else:
                    termios.tcflush(sys.stdin, termios.TCIFLUSH)
                    char = "N"

            # restore the old sys.stdin
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_stdin_parameters)

        return char


if __name__ == "__main__":
    console = Console()
    response = ConfirmationPrompt.ask(prompt="Continue", console=console, timeout=1)
    print(response)
