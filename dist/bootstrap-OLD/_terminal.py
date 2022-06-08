from io import UnsupportedOperation
import sys
import os

from _const import WINDOWS


def is_decorated():
    if WINDOWS:
        return (
            os.getenv("ANSICON") is not None
            or os.getenv("ConEmuANSI") == "ON"
            or os.getenv("Term") == "xterm"
        )

    if not hasattr(sys.stdout, "fileno"):
        return False

    try:
        return os.isatty(sys.stdout.fileno())
    except UnsupportedOperation:
        return False


class Cursor:
    def __init__(self) -> None:
        self._output = sys.stdout

    def move_up(self, lines: int = 1) -> "Cursor":
        self._output.write("\x1b[{}A".format(lines))

        return self

    def move_down(self, lines: int = 1) -> "Cursor":
        self._output.write("\x1b[{}B".format(lines))

        return self

    def move_right(self, columns: int = 1) -> "Cursor":
        self._output.write("\x1b[{}C".format(columns))

        return self

    def move_left(self, columns: int = 1) -> "Cursor":
        self._output.write("\x1b[{}D".format(columns))

        return self

    def move_to_column(self, column: int) -> "Cursor":
        self._output.write("\x1b[{}G".format(column))

        return self

    def move_to_position(self, column: int, row: int) -> "Cursor":
        self._output.write("\x1b[{};{}H".format(row + 1, column))

        return self

    def save_position(self) -> "Cursor":
        self._output.write("\x1b7")

        return self

    def restore_position(self) -> "Cursor":
        self._output.write("\x1b8")

        return self

    def hide(self) -> "Cursor":
        self._output.write("\x1b[?25l")

        return self

    def show(self) -> "Cursor":
        self._output.write("\x1b[?25h\x1b[?0c")

        return self

    def clear_line(self) -> "Cursor":
        """
        Clears all the output from the current line.
        """
        self._output.write("\x1b[2K")

        return self

    def clear_line_after(self) -> "Cursor":
        """
        Clears all the output from the current line after the current position.
        """
        self._output.write("\x1b[K")

        return self

    def clear_output(self) -> "Cursor":
        """
        Clears all the output from the cursors' current position
        to the end of the screen.
        """
        self._output.write("\x1b[0J")

        return self

    def clear_screen(self) -> "Cursor":
        """
        Clears the entire screen.
        """
        self._output.write("\x1b[2J")

        return self
