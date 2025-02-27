from __future__ import annotations

import datetime as dt
import logging
import logging.config
import logging.handlers
import pathlib
import re

from cs_tools.cli.ux import RICH_CONSOLE
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


class SecretsFilter(logging.Filter):
    """Filter to mask sensitive data in log messages."""

    def __init__(self):
        super().__init__()
        # Patterns to match sensitive data
        self.patterns = {
            "password": (r'password[\'"]\s*:\s*[\'"][^\'\"]+[\'"]', r'password": "****"'),
            "secret_key": (r'secret_key[\'"]\s*:\s*[\'"][^\'\"]+[\'"]', r'secret_key": "****"'),
            "token": (r'token[\'"]\s*:\s*[\'"][^\'\"]+[\'"]', r'token": "****"'),
            "authorization": (r"authorization\s*:\s*bearer\s+\S+", r"authorization: bearer ****"),
            # ADD MORE PATTERNS AS NEEDED
        }

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            # Apply each pattern
            for pattern, replacement in self.patterns.values():
                msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
            record.msg = msg

        # Handle args if present
        if record.args:
            args = []
            for arg in record.args:
                if isinstance(arg, str):
                    masked_arg = arg
                    for pattern, replacement in self.patterns.values():
                        masked_arg = re.sub(pattern, replacement, masked_arg, flags=re.IGNORECASE)
                    args.append(masked_arg)
                else:
                    args.append(arg)
            record.args = tuple(args)

        return True


def _setup_logging() -> None:
    """Setup CLI / application logging."""
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
        "filters": {
            "secrets": {
                "()": "cs_tools.cli._logging.SecretsFilter",
            }
        },
        "handlers": {
            "to_console": {
                "class": "rich.logging.RichHandler",
                "level": "INFO",
                "formatter": "simple",
                "filters": ["secrets"],
                # RichHandler.__init__()
                "console": RICH_CONSOLE,
                "show_level": True,
                "rich_tracebacks": True,
                "markup": True,
                "log_time_format": "[%X]",
            },
            "to_file": {
                "()": "cs_tools.cli._logging.LimitedFileHistoryHandler",
                "level": "DEBUG",
                "formatter": "detail",
                "filters": ["secrets"],
                "filename": f"{cs_tools_venv.subdir('.logs')}/{now}.log",
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
