from typing import Any, Dict, List, TextIO
import contextlib
import logging
import pathlib
import zipfile
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
    delimiter: str = '|'
    escape_character: str = None
    zipped: bool = False
    # line_ending: str = '\r\n'

    def __post_init_post_parse__(self):
        self.directory = self.directory.resolve()

        if not self.directory.exists():
            log.info(f'{self.directory} does not exist, creating..')

            if self.zipped:
                self.directory.parent.mkdir(parents=True, exist_ok=True)
            else:
                self.directory.mkdir(parents=True, exist_ok=True)

    def dialect_params(self) -> Dict[str, Any]:
        extra = {
            'delimiter': self.delimiter,
            'escapechar': self.escape_character,
            # 'lineterminator': self.line_terminator
        }
        return extra

    @contextlib.contextmanager
    def file_reference(self, file: str, mode: str) -> TextIO:
        """
        Handle open-close on a file, potentially in a zip archive.
        """
        file_opts = {
            'mode': 'r' if mode == 'r' else 'w',
            'encoding': 'utf-8',
            'newline': ''
        }

        if self.zipped:
            p = self.directory.with_suffix('.zip')
            z = util.ZipFile(p, mode=mode, compression=zipfile.ZIP_DEFLATED)
            f = z.open(file, **file_opts)
        else:
            f = (self.directory / file).open(**file_opts)

        try:
            yield f
        finally:
            f.close()

            if self.zipped:
                z.close()

    def __repr__(self):
        path = self.directory.with_suffix('.zip') if self.zipped else self.directory
        return f"<CSV sync: path='{path}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return 'csv'

    def load(self, directive: str) -> List[Dict[str, Any]]:
        with self.file_reference(f'{directive}.csv', mode='r') as f:
            reader = csv.DictReader(f, **self.dialect_params())
            data = [row for row in reader]

        return data

    def dump(self, directive: str, *, data: List[Dict[str, Any]]) -> None:
        header = data[0].keys()

        with self.file_reference(f'{directive}.csv', mode='a') as f:
            writer = csv.DictWriter(f, fieldnames=header, **self.dialect_params())
            writer.writeheader()
            writer.writerows(data)
