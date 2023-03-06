from pynput.keyboard import Controller, Key, KeyCode
from rich.prompt import PromptBase


class ConfirmationPrompt(PromptBase):

    def __init__(self, prompt: str, *, console, timeout: int = 60):
        super().__init__(prompt, console=console, choices=["y", "N"])
        self.prompt_suffix = ""
        self.timeout = timeout
        self.waiting = False
        self.response = None
        self.kb = Controller()

    def handle_kb_input(self, key):
        if key == KeyCode.from_char("y"):
            self.waiting = False
            self.response = "y"

        if key == KeyCode.from_char("n"):
            self.waiting = False
            self.response = "n"

        self.kb.press(Key.backspace)

    def ask(self, with_prompt: bool = True) -> bool:
        from pynput import keyboard
        import time

        with keyboard.Listener(on_press=self.handle_kb_input, suppress=True):
            self.waiting = True
            self._started_at = time.perf_counter()

            if with_prompt:
                self.console.print(self.make_prompt(...))

            while self.waiting:
                time.sleep(0.1)

                if (time.perf_counter() - self._started_at) > self.timeout:
                    self.waiting = False
                    self.response = "n"
                    break

        return self.response == "y"
