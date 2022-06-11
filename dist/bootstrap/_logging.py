from logging import LogRecord
from pathlib import Path
import tempfile
import logging

from _const import WINDOWS


class ColorSupportedFormatter(logging.Formatter):
    """
    Fancy formatter, intended for output to a terminal.

    Parameters
    ----------
    skip_common_time: bool  [default: True]
      whether or not to repeat the same time format for each line

    **passthru
      keywords to send to logging.Formatter
    """
    COLOR_CODES = {
        logging.CRITICAL: "\033[1;35m",  # bold magenta
        logging.ERROR: "\033[1;31m",     # bold red
        logging.WARNING: "\033[1;33m",   # bold yellow
        logging.INFO: "\033[0;37m",      # white
        logging.DEBUG: "\033[1;30m"      # bold dark gray
    }

    def __init__(self, skip_common_time: bool = True, **passthru):
        fmt = passthru.get('fmt', logging.BASIC_FORMAT)
        passthru['fmt'] = f'%(color_code)s{fmt}%(color_reset)s'
        super().__init__(**passthru)
        self._skip_common_time = skip_common_time
        self._last_time = None
        self._original_datefmt = str(self.datefmt)
        self._try_enable_ansi_terminal_mode()

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

        if self._skip_common_time:
            formatted_time = self.formatTime(record, self._original_datefmt)

            if self._last_time == formatted_time:
                self.datefmt = len(formatted_time) * " "
            else:
                self.datefmt = self._original_datefmt
                self._last_time = formatted_time

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
