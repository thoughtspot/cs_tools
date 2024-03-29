from typing import TextIO, List, Dict, Any
import contextlib
import zipfile
import pathlib
import logging
import csv

from pydantic.dataclasses import dataclass

from . import util

log = logging.getLogger(__name__)


@dataclass
class CSV:
    """
    Interact with CSV.
    """

    directory: pathlib.Path
    delimiter: str = "|"
    escape_character: str = None
    zipped: bool = False
    # line_ending: str = '\r\n'
    date_time_format: str = "%Y-%m-%d %H:%M:%S"

    def __post_init_post_parse__(self):
        self.directory = self.directory.resolve()

        if not self.directory.exists():
            log.info(f"{self.directory} does not exist, creating..")

            if self.zipped:
                self.directory.parent.mkdir(parents=True, exist_ok=True)
            else:
                self.directory.mkdir(parents=True, exist_ok=True)

    def dialect_params(self) -> Dict[str, Any]:
        extra = {
            "delimiter": self.delimiter,
            "escapechar": self.escape_character,
            # 'lineterminator': self.line_terminator
        }
        return extra

    @contextlib.contextmanager
    def file_reference(self, file: str, mode: str) -> TextIO:
        """
        Handle open-close on a file, potentially in a zip archive.
        """
        if self.zipped:
            p = self.directory.with_suffix(".zip")
            z = util.ZipFile(p, mode=mode, compression=zipfile.ZIP_DEFLATED)
            f = z.open(file, mode="r" if mode == "r" else "w")
        else:
            f = self.directory.joinpath(file).open(mode="r" if mode == "r" else "w", newline="", encoding="utf-8")

        try:
            yield f
        finally:
            f.close()

            if self.zipped:
                z.close()

    def __repr__(self):
        path = self.directory.with_suffix(".zip") if self.zipped else self.directory
        return f"<CSV sync: path='{path}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return "csv"

    def load(self, directive: str) -> List[Dict[str, Any]]:
        with self.file_reference(f"{directive}.csv", mode="r") as f:
            reader = csv.DictReader(f, **self.dialect_params())
            data = list(reader)

        return data

    def dump(self, directive: str, *, data: List[Dict[str, Any]]) -> None:
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        # in case we have the first row not include some data
        header = max([_.keys() for _ in data])

        with self.file_reference(f"{directive}.csv", mode="a") as f:
            writer = csv.DictWriter(f, fieldnames=header, **self.dialect_params())
            writer.writeheader()
            writer.writerows([util.clean_datetime(row, date_time_format=self.date_time_format) for row in data])
