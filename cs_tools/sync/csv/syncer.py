from typing import Any, Dict, List, TextIO
import contextlib
import logging
import pathlib
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
    zipped: bool = False

    def __post_init_post_parse__(self):
        self.directory = self.directory.resolve()

        if not self.directory.exists():
            log.info(f'{self.directory} does not exist, creating..')

            if self.zipped:
                self.directory.parent.mkdir(parents=True, exist_ok=True)
            else:
                self.directory.mkdir(parents=True, exist_ok=True)

    def __repr__(self):
        path = self.directory.with_suffix('.zip') if self.zipped else self.directory
        return f"<CSV sync: path='{path}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return 'csv'

    @contextlib.contextmanager
    def file_reference(self, file: str, mode: str) -> TextIO:
        """
        Handle open-close on a file, potentially in a zip archive.
        """
        if self.zipped:
            z = util.ZipFile(self.directory.with_suffix('.zip'), mode=mode)
            f = z.open(file, mode='r' if mode == 'r' else 'w')
        else:
            f = (self.directory / file).open(mode='r' if mode == 'r' else 'w')

        try:
            yield f
        finally:
            f.close()

            if self.zipped:
                z.close()

    def load(self, directive: str) -> List[Dict[str, Any]]:
        with self.file_reference(f'{directive}.csv', mode='r') as f:
            reader = csv.DictReader(f)
            data = [row for row in reader]

        return data

    def dump(self, directive: str, *, data: List[Dict[str, Any]]) -> None:
        header = data[0].keys()

        with self.file_reference(f'{directive}.csv', mode='a') as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(data)
