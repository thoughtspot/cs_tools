from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable, Literal, Optional, TypeVar
import contextlib
import functools as ft
import time

from rich.columns import Columns
from rich.console import Console, ConsoleOptions, Measurement, RenderableType, RenderResult
from rich.live import Live
from rich.style import Style
from rich.styled import Styled
from rich.text import Text
import pydantic

from cs_tools._compat import Self
from cs_tools.cli.input import KeyboardListener, Keys
from cs_tools.datastructures import _GlobalModel

T = TypeVar("T")


@contextlib.contextmanager
def timer(seconds: float = 1.25, mode: Literal["timeout", "wait"] = "timeout") -> Iterable:
    """Wait for or Timeout after a certain amount of time."""
    start = time.perf_counter()
    yield

    while mode == "wait" and (time.perf_counter() - start) <= seconds:
        time.sleep(0.025)


def loop_first_last(values: Iterable[T]) -> Iterable[tuple[bool, bool, T]]:
    """Iterate and generate a tuple with a flag for first and last value."""
    iter_values = iter(values)
    try:
        previous_value = next(iter_values)
    except StopIteration:
        return
    first = True
    for value in iter_values:
        yield first, False, previous_value
        first = False
        previous_value = value
    yield first, True, previous_value


def loop_first(values: Iterable[T]) -> Iterable[tuple[bool, T]]:
    """Iterate and generate a tuple with a flag for first value."""
    iter_values = iter(values)
    try:
        value = next(iter_values)
    except StopIteration:
        return
    yield True, value
    for value in iter_values:
        yield False, value


class PromptMarker:
    """Constants used in Prompting."""

    # PROMPT ACTIVITY
    STEP_INACTIVE = "-"
    STEP_ACTIVE = "◆"
    STEP_CANCEL = "◈"
    STEP_ERROR = "✦"
    STEP_SUBMIT = "◇"

    # LEFT HAND RAIL
    RAIL_BEG = "┌"
    RAIL_BAR = "│"
    RAIL_END = "└"

    # UI CONTROLS
    UI_RADIO_ACTIVE = "●"
    UI_RADIO_INACTIVE = "○"
    UI_CHECK_ACTIVE = "◼"
    UI_CHECK_INACTIVE = "◻"


class BasePrompt(_GlobalModel):
    """A base class for Prompts."""

    prompt: RenderableType
    status: Literal["INACTIVE", "ACTIVE", "SUCCESS", "CANCEL", "ERROR"] = "INACTIVE"

    _is_interactive: bool = False
    _marker_map = {
        "INACTIVE": PromptMarker.STEP_INACTIVE,
        "ACTIVE": PromptMarker.STEP_ACTIVE,
        "SUCCESS": PromptMarker.STEP_SUBMIT,
        "CANCEL": PromptMarker.STEP_CANCEL,
        "ERROR": PromptMarker.STEP_ERROR,
    }
    _style_map = {
        "INACTIVE": Style(color="white", bold=True, dim=True),
        "ACTIVE": Style(color="white", bold=True),
        "SUCCESS": Style(color="green", bold=True),
        "CANCEL": Style(color="red", bold=True),
        "ERROR": Style(color="red", bold=True),
    }

    @property
    def is_interactive(self) -> bool:
        """Determine if the a Prompt is interactive."""
        return self._is_interactive

    @property
    def is_active(self) -> bool:
        """Determine if the a Prompt is active."""
        return self.status == "ACTIVE"

    @property
    def marker(self) -> str:
        return self._marker_map[self.status]

    @property
    def style(self) -> Style:
        return self._style_map[self.status]

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        """Describes the the min/max number of characters required to render."""
        sized_content = Measurement.get(console, options, self.prompt)
        return sized_content.with_maximum(options.max_width)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        yield self.prompt

    def __enter__(self) -> Self:
        self.status = "ACTIVE"
        return self

    def __exit__(self, class_, exception, traceback) -> bool:
        if exception is None:
            self.status = "SUCCESS"
        elif isinstance(exception, KeyboardInterrupt):
            self.status = "CANCEL"
        else:
            # We'll ignore the error, but store it on the Prompt itself.
            self.status = "ERROR"
            self.exception = exception

        # return True

    def process_interaction(self, live: Live) -> None:
        """Allow a Prompt to get feedback from the User."""
        # raise NotImplementedError
        # with timer(mode="wait"):
        #     pass
        time.sleep(0.5)


class Select(BasePrompt):
    """Ask the User to choose from a list of options."""

    choices: list[str]
    mode: Literal["single", "multi", "custom"]
    choice_validator: Optional[Callable[[str], Any]] = None

    _answer: Any = None
    _is_interactive: bool = True

    def select(self, choices: list[str]) -> None:
        """Make a selection."""
        self._answer = choices

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        yield self.prompt

        if self.is_active:
            yield self.draw_selector()
        else:
            yield self.draw_selected()


class UserTextInput(BasePrompt):
    """Ask the User to type a response"""

    validator: Optional[Callable[[str], Any]] = None
    is_secret: bool = False

    _buffer: list[str] = pydantic.PrivateAttr(default_factory=list)
    _validated_input: Optional[str] = None
    _is_interactive: bool = True

    @property
    def screen_friendly_buffer(self) -> str:
        buffer = self._buffer if self._validated_input is None else self._validated_input
        return "".join(["?" if self.is_secret else c for c in buffer])

    def _input_to_screen(self, live: Live):
        """ """
        with KeyboardListener(console=live.console) as kb:
            while kb.is_running:
                key = kb.get()

                if key == Keys.BACKSPACE:
                    self._buffer.pop()

                if key.is_printable:
                    self._buffer.append(key.character)

                live.refresh()

                if key == Keys.ENTER:
                    kb.stop()
                    break

    def process_interaction(self, live: Live):
        """ """
        while self._validated_input is None:
            self._input_to_screen(live=live)

            if self.validator is not None and not self.validator(self._buffer):
                if "Invalid input" not in self.prompt:
                    self.prompt = f"{self.prompt} [dim white]>>[/] [b red]Invalid input, please try again.[/]"
    
                self._buffer.clear()
                live.refresh()
                continue

            self._validated_input = "".join(self._buffer)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        yield self.prompt
        yield self.screen_friendly_buffer


class Confirm(Select):
    """Ask the User a Yes/No question."""

    default: Literal["Yes", "No"]
    _is_interactive: bool = True

    def __init__(self, **options):
        super().__init__(choices=["Yes", "No"], mode="single", **options)
        self._answer = self.default

    def select(self, choice: str) -> None:  # type: ignore[override]
        """Make a selection."""
        self._answer = choice

    def draw_selector(self) -> Text:
        """Show the choices on screen."""
        choices = []

        for value in ("Yes", "No"):
            selected = self._answer == value
            marker = PromptMarker.UI_RADIO_ACTIVE if selected else PromptMarker.UI_RADIO_INACTIVE
            choice = Text(text=f"{marker} {value}", style=Style(color="white", bold=True, dim=not selected))
            choices.append(choice)

        return Text(text=" / ").join(choices)

    def draw_selected(self) -> Text:
        return Text(text=f"{PromptMarker.UI_RADIO_ACTIVE} {self._answer}", style="bold dim white")

    def process_interaction(self, live: Live) -> None:
        """ """
        with KeyboardListener(console=live.console) as kb:
            while kb.is_running:
                key = kb.get()

                if key == Keys.char("Q"):
                    kb.stop()
                    break

                if key in (Keys.char("Y"), Keys.char("N")):
                    self.select(choice="Yes" if key == Keys.char("Y") else "No")

                if key in (Keys.LEFT, Keys.RIGHT):
                    self.select(choice="No" if self._answer == "Yes" else "Yes")

                live.refresh()

                if key == Keys.ENTER:
                    break

                if key == Keys.ESCAPE:
                    self.status = "CANCEL"


class Note(BasePrompt):
    """Print an informative message."""

    _is_interactive: bool = False


class PromptMenu(_GlobalModel):
    """Draw an interactive menu."""

    introduction: str
    prompts: list[pydantic.InstanceOf[BasePrompt]]
    epilog: Optional[str] = None

    @pydantic.model_validator(mode="after")
    def _convert_to_note_prompts(self) -> PromptMenu:
        self.prompts.insert(0, Note(prompt=self.introduction))

        if self.epilog is not None:
            self.prompts.append(Note(prompt=self.epilog))

        return self

    @property
    def number_of_prompts(self) -> int:
        return len(self.prompts)

    def draw_columns(self, prompt: BasePrompt, *, marker, console: Console, options: ConsoleOptions) -> list[Columns]:
        """ """
        ACTIVE_STYLE = Style(color="blue", bold=True)
        NULL_STYLE = Style.null()
        DIM_STYLE = Style(color="white", bold=True, dim=True)
        STRIKE_STYLE = Style(color="white", bold=True, dim=True, strike=True)

        columns = []
        segments = prompt.__rich_console__(console=console, options=options)

        for is_first_segment, segment in loop_first(segments):
            if not is_first_segment:
                marker = PromptMarker.RAIL_BAR
                style = DIM_STYLE if prompt.status == "SUCCESS" else STRIKE_STYLE
            else:
                marker = Styled(marker, style=prompt.style)
                style = NULL_STYLE if prompt.status == "SUCCESS" else prompt.style

            styled_segment = Styled(segment, style=ACTIVE_STYLE if prompt.is_active else style)
            columns.append(Columns([marker, styled_segment]))

        return columns

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        segments = ft.partial(self.draw_columns, console=console, options=options)

        for is_first_prompt, is_last_prompt, prompt in loop_first_last(self.prompts):
            if prompt.status == "INACTIVE":
                continue

            if is_first_prompt:
                yield Columns([PromptMarker.RAIL_BEG if not prompt.is_active else prompt.marker, prompt])
                continue

            yield Columns([PromptMarker.RAIL_BAR])

            if is_last_prompt:
                yield Columns([PromptMarker.RAIL_END, prompt])
                continue

            yield from segments(prompt, marker=prompt.marker)

            if prompt.is_active:
                yield Columns([PromptMarker.RAIL_END])

    def begin(self, console: Console) -> None:
        """Progress through all prompts."""
        with Live(self, console=console, auto_refresh=False) as live:
            for prompt in self.prompts:
                with prompt:
                    live.update(self, refresh=True)

                    if prompt.is_interactive:
                        prompt.process_interaction(live=live)

                if prompt.status == "ERROR":
                    break

            live.update(self, refresh=True)


if __name__ == "__main__":
    nav = PromptMenu(
        introduction="Welcome to CS Tools!",
        prompts=[
            Note(prompt="Let's set up a configuration file."),
            Confirm(prompt="Directory not empty. Continue?", default="No"),
            UserTextInput(prompt="What's your favorite flower?", validator=lambda b: len(b) > 0),
        ],
        epilog="Complete!",
    )

    try:
        nav.begin(console=Console())
    except KeyboardInterrupt:
        pass
