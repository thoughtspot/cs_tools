from logging import LogRecord
from pathlib import Path
import tempfile
import logging

from _const import WINDOWS
from _types import LogLevel


def add_logging_level(level_name: str, level_number: int) -> None:
    """
    Adds a new logging level to the `logging` module.

    Parameters
    ----------
    level_name: str
      text logging level

    level_number: int
      numeric logging level
    """
    method__name__ = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError('{} already defined in logging module'.format(level_name))

    if hasattr(logging, method__name__):
        raise AttributeError('{} already defined in logging module'.format(method__name__))

    if hasattr(logging.getLoggerClass(), method__name__):
        raise AttributeError('{} already defined in logger class'.format(method__name__))

    # This method was inspired by the answers to Stack Overflow post
    #   http://stackoverflow.com/q/2183233/2988730, especially
    #   http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message: str, *args, **kwargs) -> None:
        if self.isEnabledFor(level_number):
            self._log(level_number, message, args, **kwargs)

    def logToRoot(message: str, *args, **kwargs) -> None:
        logging.log(level_number, message, *args, **kwargs)

    logging.addLevelName(level_number, level_name)
    setattr(logging, level_name, level_number)
    setattr(logging.getLoggerClass(), method__name__, logForLevel)
    setattr(logging, method__name__, logToRoot)


def _create_color_code(color: str, *, bold: bool = False) -> str:
    # See: https://stackoverflow.com/a/33206814
    escape_sequence = '\033['
    end_sequence = 'm'

    foreground_color_map = {
        "black": 30,  # dark gray
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "magenta": 35,
        "cyan": 36,
        "white": 37,
    }

    if color not in foreground_color_map:
        raise ValueError(f"invalid terminal color code: '{color}'")

    to_bold = int(bold)  # 0 = reset , 1 = bold
    to_color = foreground_color_map[color]
    return f'{escape_sequence}{to_bold};{to_color}{end_sequence}'


class ColorSupportedFormatter(logging.Formatter):
    """
    Fancy formatter, intended for output to a terminal.

    The log record format itself is fairly locked to look like..

     11:13:51 | Welcome to the CS Tools Installation script!
              |
              |     [PLATFORM DETAILS]
              |     system: Windows (detail: Windows-10-10.0.19041-SP0)
              |     platform tag 'win-amd64'
              |     python: 3.10.4
              |     ran at: 2022-06-12 11:13:51
              |

    Parameters
    ----------
    skip_common_time: bool  [default: True]
      whether or not to repeat the same time format for each line

    indent_amount: int  [default: 2]
      number of spaces to indent child messages by

    **passthru
      keywords to send to logging.Formatter
    """
    COLOR_CODES = {
        logging.CRITICAL: _create_color_code("magenta", bold=True),
        logging.ERROR: _create_color_code("red", bold=True),
        logging.WARNING: _create_color_code("yellow", bold=True),
        logging.INFO: _create_color_code("white"),
        logging.DEBUG: _create_color_code("black", bold=True),
    }

    def __init__(self, skip_common_time: bool = True, indent_amount: int = 2, **passthru):
        passthru['fmt'] = "%(asctime)s %(color_code)s| %(indent)s%(message)s%(color_reset)s"
        super().__init__(**passthru)
        self._skip_common_time = skip_common_time
        self._indent_amount = indent_amount
        self._last_time = None
        self._original_datefmt = str(self.datefmt)
        self._try_enable_ansi_terminal_mode()

    def add_color_level(self, level: LogLevel, *, color: str, bold: bool = False) -> None:
        """
        Colorizes the logging level.

        Parameters
        ----------
        level: int
          logging module's levelNo to colorize

        color: str
          name of the color to use

        bold: bool  [default: False]
          whether or not to bold the color
        """
        self.COLOR_CODES[level] = _create_color_code(color, bold=bold)

    def _try_enable_ansi_terminal_mode(self) -> None:
        # See: https://stackoverflow.com/a/36760881
        if not WINDOWS:
            return

        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    def format(self, record: LogRecord, *a, **kw) -> str:
        color = self.COLOR_CODES.get(record.levelno, "\033[0;37m")  # default to white
        record.color_code = color
        record.color_reset = "\033[0m"
        record.indent = ""

        # skip repeating the time format if it hasn't changed since last log
        formatted_time = self.formatTime(record, self._original_datefmt)

        if self._skip_common_time:
            if self._last_time == formatted_time:
                self.datefmt = len(formatted_time) * " "
            else:
                self.datefmt = self._original_datefmt
                self._last_time = formatted_time

        # add indentations
        if 'parent' in record.__dict__:
            parents = record.__dict__['parent'].count(".") + 1
            indents = parents * self._indent_amount * " "
            record.indent = indents

        # force newlines to respect indentation
        record.message = record.getMessage()
        record.asctime = formatted_time
        s = self.formatMessage(record)
        prefix, _, _ = s.partition(record.msg[:10])
        prefix = prefix.replace(formatted_time, len(formatted_time) * " ")
        record.msg = record.msg.replace("\n", f"\n{prefix}")

        return super().format(record, *a, **kw)


class InMemoryUntilErrorHandler(logging.FileHandler):
    """
    A handler which stores lines in memory until an error is reached,
    and only then writes to file.

    If no error is reached during execution of the program, a logfile will not
    be generated. Once the first error is found, the entire buffer will drain
    into the logfile, with the error itself being the final stub of the file.

    Parameters
    ----------
    directory: pathlib.Path
      base directory to write the logfile to

    prefix: str
      filename identifier, this will have a random suffix attached

    **passthru
      keywords to send to logging.FileHandler
    """
    def __init__(self, directory: Path, prefix: str, **passthru):
        super().__init__(**passthru, filename='NULL.log', delay=True)
        self._buffer = []
        self._found_error = False
        self._dir = directory
        self._prefix = prefix

    def emit(self, record: LogRecord) -> None:
        if self._found_error:
            super().emit(record)
            return

        if record.levelno < logging.ERROR:
            self._buffer.append(record)
            return

        self._found_error = True

        # "baseFilename" is how the FileHandler calls it
        _, self.baseFilename = tempfile.mkstemp(
            suffix=".log",
            prefix=self._prefix,
            dir=self._dir,
            text=True
        )

        for prior_record in self._buffer:
            super().emit(prior_record)

        super().emit(record)
