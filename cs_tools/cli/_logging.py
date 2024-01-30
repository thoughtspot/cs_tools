from __future__ import annotations

import datetime as dt
import logging
import logging.config
import logging.handlers
import pathlib

from cs_tools.cli.ux import rich_console
from cs_tools.updater import cs_tools_venv


class LimitedFileHistoryHandler(logging.FileHandler):
    """Only keep so many log files."""

    def __init__(self, max_files_to_keep: int, **kwargs):
        super().__init__(**kwargs)
        self.base_directory = pathlib.Path(self.baseFilename).parent
        self.max_files_to_keep = max_files_to_keep

        if not self.delay:
            self._check_if_should_clean()

    def _check_if_should_clean(self) -> None:
        """Rotate log history if needed."""
        if not self.base_directory.exists():
            return

        lifo = sorted(self.base_directory.iterdir(), reverse=True)

        for idx, log in enumerate(lifo):
            if idx >= self.max_files_to_keep:
                log.unlink()

    def emit(self, record: logging.LogRecord) -> None:
        """Don't open a new file unless we actually emit a log line."""
        if self.stream is None:
            self.stream = self._open()
            self._check_if_should_clean()

        super().emit(record)


def _setup_logging() -> None:
    """Setup CLI / application logging."""
    logs_dir = cs_tools_venv.app_dir.joinpath(".logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y-%m-%dT%H_%M_%S")

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {"format": "%(message)s"},
            "detail": {
                "format": "[%(levelname)s - %(asctime)s] [%(name)s - %(module)s.%(funcName)s %(lineno)d] %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
        },
        "handlers": {
            "to_console": {
                "class": "rich.logging.RichHandler",
                "level": "INFO",
                "formatter": "simple",
                # RichHandler.__init__()
                "console": rich_console,
                "show_level": True,
                "rich_tracebacks": True,
                "markup": True,
                "log_time_format": "[%X]",
            },
            "to_file": {
                "()": "cs_tools.cli._logging.LimitedFileHistoryHandler",
                "level": "DEBUG",
                "formatter": "detail",
                "filename": f"{logs_dir}/{now}.log",
                "mode": "w",
                "max_files_to_keep": 25,
                "encoding": "utf-8",
                "delay": True,
            },
        },
        "loggers": {
            "root": {
                "level": "DEBUG",
                "handlers": [
                    "to_console",
                    "to_file",
                ],
            }
        },
    }

    logging.config.dictConfig(config)

    # HTTPX has gotten quite noisy since
    logging.getLogger("httpcore").setLevel("WARNING")
    logging.getLogger("httpx").setLevel("WARNING")
