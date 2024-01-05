from __future__ import annotations

from collections.abc import Iterable
from types import TracebackType
from typing import Annotated, Any, Callable, Literal, Optional, Union
import logging
import time
import uuid

from rich._loop import loop_first_last
from rich.console import Console, ConsoleOptions, Group, Measurement, RenderableType, RenderResult
from rich.live import Live
from rich.segment import Segment
from rich.style import Style
from rich.styled import Styled
from rich.text import Text
import pydantic

from cs_tools._compat import Self, StrEnum
from cs_tools.cli.input import KeyboardListener, Keys
from cs_tools.datastructures import _GlobalModel

log = logging.getLogger(__name__)


def _noop_always_valid(prompt: BasePrompt, answer: Any) -> bool:  # noqa: ARG001
    """An input validator that always returns True."""
    return True


class PromptMarker(StrEnum):
    """Constants used in Prompting."""

    # LEFT HAND RAIL
    RAIL_BEG = "┌"
    RAIL_BAR = "│"
    RAIL_END = "└"

    # UI CONTROLS
    UI_RADIO_ACTIVE = "●"
    UI_RADIO_INACTIVE = "○"
    UI_CHECK_ACTIVE = "◼"
    UI_CHECK_INACTIVE = "◻"


class PromptOption(_GlobalModel):
    """Represent a choice a User can make."""

    text: str
    description: Optional[str] = None
    is_selected: bool = False
    is_highlighted: bool = False

    def toggle(self) -> None:
        """Flip the value of .is_selected."""
        self.is_selected = False if self.is_selected else True


class PromptStatus(_GlobalModel):
    """Represent a themed status for a Prompt."""

    status: Annotated[str, pydantic.StringConstraints(to_upper=True)]
    marker: Annotated[str, pydantic.StringConstraints(max_length=1)]
    style: Style

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PromptStatus):
            return self.status == other.status

        if isinstance(other, str):
            return self.status == other

        return NotImplemented

    def __rich__(self) -> Text:
        styled_status = Text(self.status, style=self.style)
        return Text(f"<PromptStatus {self.marker} ") + styled_status + Text(">")

    def __str__(self) -> str:
        return self.__rich__().plain

    @classmethod
    def hidden(cls) -> Self:
        """State the Prompt is in before starting."""
        return cls(status="HIDDEN", marker="-", style=Style(color="white", bold=True, dim=True))

    @classmethod
    def active(cls) -> Self:
        """State the Prompt is in when it's the live modal."""
        return cls(status="ACTIVE", marker="◆", style=Style(color="blue", bold=True))

    @classmethod
    def success(cls) -> Self:
        """State the Prompt is in when interactivity finished successfully."""
        return cls(status="SUCCESS", marker="◇", style=Style(color="green", bold=True))

    @classmethod
    def warning(cls) -> Self:
        """State the Prompt is in when interactivity was terminated by the user."""
        return cls(status="WARNING", marker="◈", style=Style(color="yellow", bold=True))

    @classmethod
    def error(cls) -> Self:
        """State the Prompt is in when interactivity finished unsuccessfully."""
        return cls(status="ERROR", marker="✦", style=Style(color="red", bold=True))

    @classmethod
    def cancel(cls) -> Self:
        """State the Prompt is in when interactivity was terminated by the user."""
        return cls(status="CANCEL", marker="◈", style=Style(color="red", bold=True, dim=True))


class BasePrompt(_GlobalModel):
    """A base class for Prompts."""

    id: str = pydantic.Field(default_factory=lambda: uuid.uuid4().hex)
    prompt: RenderableType
    detail: Optional[RenderableType] = None
    transient: bool = False
    prompt_status_class: type[PromptStatus] = PromptStatus

    _warning: Optional[str] = None
    _exception: Optional[BaseException] = None
    _status: PromptStatus = PromptStatus.hidden()

    @property
    def status(self) -> PromptStatus:
        """Retrieve the prompt's status."""
        return self._status

    @status.setter
    def status(self, value: Union[str, PromptStatus]) -> None:
        """Set the prompt's status."""
        if isinstance(value, self.prompt_status_class):
            self._status = value
            return

        assert isinstance(value, str)

        try:
            cls_status_method = getattr(self.prompt_status_class, value)
        except AttributeError:
            raise ValueError(f"{self.prompt_status_class.__name__} does not define status '{value}'") from None

        self._status = cls_status_method()

    @property
    def is_active(self) -> bool:
        """Determine if the Prompt is active."""
        return self.status in (PromptStatus.active(), PromptStatus.warning())

    @property
    def warning(self) -> Optional[str]:
        """Retrieve the warning message, if one is set."""
        return self._warning

    @warning.setter
    def warning(self, message: str) -> None:
        self._warning = message
        self._status = PromptStatus.warning()

    @property
    def exception(self) -> Optional[BaseException]:
        """Retrieve the exception, if one occurred."""
        return self._exception

    @exception.setter
    def exception(self, exception: Exception) -> None:
        self._exception = exception
        self._status = PromptStatus.error()

    @property
    def marker(self) -> str:
        """Retrieve the appropriate prompt marker."""
        return self.status.marker

    @property
    def style(self) -> Style:
        """Retrieve the appropriate prompt style."""
        return self.status.style

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        """Describes the the min/max number of characters required to render."""
        sized_content = Measurement.get(console, options, self.prompt)
        return sized_content.with_maximum(options.max_width)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        yield self.prompt

        if self.is_active and self.warning is not None:
            yield Text.from_markup(f"X [dim white]>>[/] {self.warning}", style=self.style)

        if self.is_active and self.detail is not None and self.warning is None:
            yield Styled(self.detail, style="dim white")

    def __enter__(self) -> Self:
        self.status = PromptStatus.active()
        return self

    def interactivity(self, live: Live) -> None:
        """Allow a Prompt to get feedback from the User."""
        # Override in a subclass to implement functionality.
        pass

    def __exit__(self, class_: type[BaseException], exception: BaseException, traceback: TracebackType) -> bool:
        if exception is None and self.is_active:
            self.status = PromptStatus.success() if not self.transient else PromptStatus.hidden()

        # If we're not active while exiting, then the status was set intentionally.
        elif exception is None and self.status == PromptStatus.cancel():
            pass

        elif isinstance(exception, KeyboardInterrupt):
            self.status = PromptStatus.cancel()

        # We'll ignore the error, but store it on the Prompt itself.
        else:
            self.status = PromptStatus.error()
            self.exception = exception
            log.error(
                f"{class_.__name__} occurred in {self.__class__.__name__} prompt, check .exception or see DEBUG log "
                f"for details..",
                exc_info=True,
            )
            log.debug("Full error..", exc_info=True)

        return True


class UserTextInput(BasePrompt):
    """Ask the User to type a response"""

    is_secret: bool = False
    input_validator: Callable[[BasePrompt, str], bool] = pydantic.Field(default=_noop_always_valid)
    """Validates the input, sets a warning if the selection is in an invalid state."""

    _buffer: list[str] = pydantic.PrivateAttr(default_factory=list)
    _is_validated: bool = False

    def buffer_as_string(self, *, on_screen: bool = False) -> str:
        """Render the buffer."""
        buffer = self._buffer

        if on_screen and self.is_secret:
            buffer = ["?" for character in self._buffer]

        return "".join(buffer)

    def _simulate_py_input(self, live: Live) -> None:
        """
        Pretend to be a python-native input() function.

        Uses a keyboard listener to trigger Live.refresh() on every key.
        """
        with KeyboardListener() as kb:
            while kb.is_running:
                key = kb.get()

                if key in (Keys.BACKSPACE, Keys.LEFT) and self._buffer:
                    self._buffer.pop()

                if key.is_printable:
                    assert key.character is not None
                    self._buffer.append(key.character)

                live.refresh()

                if key == Keys.ENTER:
                    kb.stop()

                if key == Keys.ESCAPE:
                    self.status = PromptStatus.cancel()
                    kb.stop()

    def set_buffer(self, user_input: str) -> None:
        """Directly set the underlying buffer."""
        self._buffer = list(user_input)

    def interactivity(self, live: Live) -> None:
        """Handle taking input from the User."""
        original_prompt = str(self.prompt)

        while not self._is_validated:
            self._simulate_py_input(live=live)

            if self.status == PromptStatus.cancel():
                break

            if not self.input_validator(self, self.buffer_as_string()):
                self._buffer.clear()
                live.refresh()
                continue

            self.prompt = original_prompt
            self._is_validated = True

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        yield from super().__rich_console__(console=console, options=options)

        buffered_text = self.buffer_as_string(on_screen=True)

        if self.is_active and self.is_secret:
            self.detail = f"..currently {len(buffered_text)} characters"
            yield Text(buffered_text, style=Style(color="white", bgcolor="blue", bold=True))
        elif self.is_active:
            yield Text(buffered_text, style="bold white on blue")
        else:
            yield buffered_text


class Select(BasePrompt):
    """Ask the User to choose from a list of options."""

    choices: list[PromptOption]
    mode: Literal["SINGLE", "MULTI"]
    selection_validator: Callable[[BasePrompt, list[PromptOption]], bool] = pydantic.Field(default=_noop_always_valid)
    """Validates the answer, sets a warning if the selection is in an invalid state."""

    @pydantic.model_validator(mode="before")
    @classmethod
    def _convert_string_to_choice(cls, data: Any) -> Any:
        """Ensure all choice options are PromptOptions."""
        any_are_highlighted = False

        for idx, choice in enumerate(data["choices"]):
            if isinstance(choice, str):
                data["choices"][idx] = choice = PromptOption(text=choice, is_highlighted=not idx)

            any_are_highlighted = any((any_are_highlighted, choice.is_highlighted))

        if not any_are_highlighted:
            data["choices"][0].is_highlighted = True

        return data

    @property
    def answer(self) -> list[PromptOption]:
        """Retrieve the valid answers."""
        return [option for option in self.choices if option.is_selected]

    def _get_highlighted_info(self) -> tuple[int, PromptOption]:
        """Implement a naive cursor fetcher. This could be better."""
        for idx, choice in enumerate(self.choices):
            if choice.is_highlighted:
                return (idx, choice)
        raise ValueError("No option is active.")

    def select(self, choice: str) -> None:
        """Make a selection."""
        for option in self.choices:
            if option.text == choice:
                option.toggle()

            elif self.mode == "SINGLE":
                option.is_selected = False

    def highlight(self, choice: str) -> None:
        """Highlight an option."""
        for option in self.choices:
            if option.text == choice:
                option.is_highlighted = True
            else:
                option.is_highlighted = False

    def interactivity(self, live: Live) -> None:
        """Handle selecting one of the choices from the User."""
        with KeyboardListener() as kb:
            while kb.is_running:
                key = kb.get()

                if key in (Keys.ESCAPE, Keys.char("Q")):
                    self.status = PromptStatus.cancel()
                    kb.stop()
                    continue

                if key == Keys.ENTER and self.selection_validator(self, self.answer):
                    kb.stop()
                    continue

                idx, highlighted = self._get_highlighted_info()
                more_than_one_option = len(self.choices) > 1

                if key in (Keys.RIGHT, Keys.DOWN):
                    next_idx = (idx + 1) % len(self.choices)
                    to_highlight = self.choices[next_idx]
                    self.highlight(to_highlight.text)

                    if self.mode == "SINGLE" and more_than_one_option:
                        self.select(to_highlight.text)

                if key in (Keys.LEFT, Keys.UP):
                    last_idx = (idx - 1) % len(self.choices)
                    to_highlight = self.choices[last_idx]
                    self.highlight(to_highlight.text)

                    if self.mode == "SINGLE" and more_than_one_option:
                        self.select(to_highlight.text)

                if key == Keys.SPACE and more_than_one_option:
                    self.select(highlighted.text)

                live.refresh()

    def draw_selector(self) -> Text:
        """Render the choices to select from."""
        # fmt: off
        active   = PromptMarker.UI_RADIO_ACTIVE   if self.mode == "SINGLE" else PromptMarker.UI_CHECK_ACTIVE
        hidden = PromptMarker.UI_RADIO_INACTIVE if self.mode == "SINGLE" else PromptMarker.UI_CHECK_INACTIVE
        choices  = []
        # fmt: on

        for option in self.choices:
            # fmt: off
            marker = active if option.is_selected else hidden
            focus  = option.is_highlighted and self.is_active
            color  = "green" if (focus or option.is_selected and not self.is_active) else "white"
            choice = Text(text=f"{marker} {option.text}", style=Style(color=color, bold=True, dim=not focus))

            if self.is_active or (not self.is_active and option.is_selected):
                choices.append(choice)
            # fmt: on

        return Text(text=" / ").join(choices)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        """How Rich should display the Prompt."""
        yield from super().__rich_console__(console=console, options=options)
        yield self.draw_selector()

        if self.is_active:
            highlighted = next(option for option in self.choices if option.is_highlighted)

            if highlighted.description is not None:
                yield Text(text=highlighted.description, style=Style(color="green", bold=True, italic=True, dim=True))


class Confirm(Select):
    """Ask the User a Yes/No question."""

    default: Literal["Yes", "No"]
    choice_means_stop: Optional[Literal["Yes", "No"]] = None

    def __init__(self, **options):
        default = options.get("default")
        choices = [
            PromptOption(text="Yes", is_selected="Yes" == default, is_highlighted="Yes" == default),
            PromptOption(text="No", is_selected="No" == default, is_highlighted="No" == default),
        ]
        super().__init__(choices=choices, mode="SINGLE", selection_validator=Confirm.cancel_if_stop_choice, **options)

    @classmethod
    def cancel_if_stop_choice(cls, prompt: BasePrompt, answer: list[PromptOption]) -> bool:
        """Set internal state if the answer means cancelled."""
        assert isinstance(prompt, Confirm)

        # In single-select mode, there is always only ever 1 answer.
        if answer[0].text == prompt.choice_means_stop:
            prompt.status = PromptStatus.cancel()

        return True


class Note(BasePrompt):
    """Print an informative message."""

    on_screen_time: float = 0

    def interactivity(self, live: Live) -> None:  # noqa: ARG002
        """Optionally give the User some time to read."""
        time.sleep(self.on_screen_time)


class PromptInMenu:
    """
    Prompts in the menu have a left hand rail.

      a. The first prompt in the menu will have a null-styled opening marker.
      b. All Prompts will have a .style'd status indicator shown at all times.
      c. All multi-prompts will have their non-marked lines shown as a .style'd rail.
      d. The active prompt will have the first line .style'd, with all other lines in
         the NULL_STYLE.
      e. The last line in the last prompt will have a closing marker.

    A --> ┌ cs_tools config create
          │
    B --> ◇ Please name your configuration.
    C --> │ 710
          │
          ◇ Config 710 exists, do you want to overwrite it?
          │ ● Yes / ○ No
          │
          ...
          │
    D --> ◆ Which authentication method do you want to use?
      --> │ ◻ Password / ◼ Trusted Authentication / ◻ Bearer Token
      --> │ this is the password used on the ThoughtSpot login screen
          │
          ...
          │
    E --> └ Complete!
    """

    def __init__(self, prompt: BasePrompt, position_in_menu: Literal["FIRST", "MIDDLE", "LAST"] = "MIDDLE"):
        self.prompt = prompt
        self.padding_width = 2
        self.position_in_menu = position_in_menu

    def determine_rail_marker(self, is_first_line: bool) -> str:
        """ """
        marker = {"FIRST": PromptMarker.RAIL_BEG, "MIDDLE": self.prompt.status.marker, "LAST": PromptMarker.RAIL_END}
        return marker[self.position_in_menu] if is_first_line else PromptMarker.RAIL_BAR

    def determine_rail_style(self, is_first_line: bool) -> Style:
        """ """
        style = Style.null()

        if is_first_line and self.position_in_menu == "MIDDLE":
            style = self.prompt.style

        elif self.prompt.is_active and self.prompt.warning is not None:
            style = self.prompt.style

        elif self.prompt.is_active:
            style = self.prompt.style

        elif self.prompt.status != PromptStatus.success() and not is_first_line:
            style = self.prompt.style

        return style

    def determine_line_style(self, is_first_line: bool) -> Style:
        """ """
        style = self.prompt.style

        if self.prompt.is_active and not is_first_line:
            style = Style.null()

        elif not self.prompt.is_active and is_first_line and self.prompt.status == PromptStatus.success():
            style = Style.null()

        elif not self.prompt.is_active and not is_first_line:
            style = Style(color="white", dim=True)

        return style

    def __rich_console__(self, console, options):
        NULL_STYLE = Style.null()

        render_options = options.update(max_width=options.max_width - self.padding_width)
        lines = console.render_lines(self.prompt, render_options, pad=False)

        for is_first_line, is_last_line, line in loop_first_last(lines):
            marker = self.determine_rail_marker(is_first_line)
            marker_style = self.determine_rail_style(is_first_line)
            line_style = self.determine_line_style(is_first_line)

            assert len(marker) == 1
            yield Segment(text=f"{marker} ", style=marker_style)
            yield from Segment.apply_style(line, style=NULL_STYLE, post_style=line_style)
            yield Segment("\n")

            if self.prompt.is_active and is_last_line:
                yield Segment(PromptMarker.RAIL_END, style=self.prompt.style)
                yield Segment("\n")


def reshape_and_measure(
    *renderables: RenderableType, console: Console, max_width: Optional[int] = None
) -> tuple[int, int]:
    """Gather and reshape renderables to meet the max width of the console."""
    options = console.options

    if max_width is not None:
        options = options.update(max_width=max_width)

    group = Group(*renderables)
    lines = console.render_lines(group, options, pad=False)
    shape = Segment.get_shape(lines)

    return shape


class PromptMenu:
    """
    Draw an interactive menu of prompts.

    Prompts start off in a hidden state, and only come into view as we progress
    through the menu. Transient prompts will be hidden once they've been
    interacted with.
    """

    def __init__(
        self,
        *prompts: BasePrompt,
        console: Console,
        intro: str,
        outro: Optional[str] = None,
        transient: bool = False,
    ):
        self.prompts = self.ensure_prompts(intro, *prompts, outro)
        self.console = console
        self.live = Live(
            console=console,
            auto_refresh=False,
            transient=transient,
            get_renderable=self.get_renderable,
            vertical_overflow="visible",
        )
        self.has_outro = outro is not None

    @property
    def stopped(self) -> bool:
        """Determine whether or not any of the prompts were cancelled or errored."""
        return any(prompt.status == (PromptStatus.error(), PromptStatus.cancel()) for prompt in self.prompts)

    def ensure_prompts(self, *prompts: Union[str, BasePrompt, None]) -> list[BasePrompt]:
        """Convert all menus into Prompts."""
        ensured = []

        for prompt in prompts:
            if prompt is None:
                continue

            if isinstance(prompt, str):
                prompt = Note(prompt=prompt)

            ensured.append(prompt)

        return ensured

    def __getitem__(self, prompt_id: str) -> BasePrompt:
        try:
            return next(prompt for prompt in self.prompts if prompt.id == prompt_id)
        except StopIteration:
            raise KeyError(f"No such prompt exists with .id '{prompt_id}'")

    def __rich__(self) -> RenderableType:
        """Makes the Prompt Menu class itself renderable."""
        return self.get_renderable()

    def fake_scroll(self, *, renderables: list[RenderableType], overage: int) -> list[RenderableType]:
        """Simulate scrolling of the PromptMenu."""
        trimmed = []

        for lines in renderables:
            width, height = reshape_and_measure(lines, console=self.console)
            overage = overage - height

            if overage >= -1:
                continue

            trimmed.append(lines)

        return trimmed

    def get_renderable(self) -> RenderableType:
        """Get a renderable for the prompt menu."""
        renderable_lines = self.get_renderables()
        console_width, console_height = self.console.size
        renders_width, renders_height = reshape_and_measure(*renderable_lines, console=self.console)

        if renders_height > console_height and self.live.is_started:
            renderable_lines = self.fake_scroll(renderables=renderable_lines, overage=renders_height - console_height)

        return Group(*renderable_lines)

    def get_renderables(self) -> Iterable[RenderableType]:
        """Get a number of renderables for the prompt menu."""
        renderables: list[RenderableType] = []

        for is_first_prompt, is_last_prompt, prompt in loop_first_last(self.prompts):
            if prompt.status == PromptStatus.hidden():
                continue

            if not is_first_prompt:
                renderables.append(PromptMarker.RAIL_BAR)

            position = "MIDDLE"

            if is_first_prompt:
                position = "FIRST"

            if is_last_prompt:
                position = "LAST"

            multiline_prompt = PromptInMenu(prompt, position_in_menu=position)
            renderables.append(multiline_prompt)

        return renderables

    def start(self) -> None:
        """
        Start the prompt menu.

        You should prefer to use .begin().
        """
        self.live.start()

    def stop(self, refresh: bool = True) -> None:
        """
        Stop the prmopt menu.

        You should prefer to use .begin().
        Any remaining prompts will remain hidden.
        """
        if refresh:
            self.live.refresh()

        self.live.stop()

    def handle_prompt(self, prompt: BasePrompt) -> None:
        """
        Progress through a prmopt in the menu.

        You should prefer to use .begin().
        """
        with prompt:
            self.live.refresh()

            prompt.interactivity(live=self.live)

    def add(self, prompt: BasePrompt, *, after: Optional[BasePrompt] = None) -> None:
        """Add a prompt to the menu."""
        idx = len(self.prompts) if after is None else self.prompts.index(after) + 1
        self.prompts.insert(idx, prompt)

    def begin(self) -> None:
        """Progress through all prompts."""
        self.start()

        for prompt in self.prompts:
            self.handle_prompt(prompt)

            if prompt.status in (PromptStatus.cancel(), PromptStatus.error()):
                break

        self.stop()
