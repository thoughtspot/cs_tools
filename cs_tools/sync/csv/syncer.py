from typing import Any, Dict, List
import logging
import pathlib
import csv

from pydantic.dataclasses import dataclass


log = logging.getLogger(__name__)


@dataclass
class CSV:
    """
    Interact with CSV.
    """
    directory: pathlib.Path
    zipped: bool = False

    def __post_init_post_parse__(self):
        self.path = self.path.resolve()

        if not self.path.exists():
            log.info(f'{self.path.parent} does not exist, creating..')

            if self.path.name.endswith('.json'):
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.touch()
            else:
                self.path.mkdir(parents=True, exist_ok=True)

    def __repr__(self):
        return f"<CSV sync: path='{self.path}', file={self.is_file()}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return 'json'

    def load(self, directive: str) -> List[Dict[str, Any]]:
        path = self.path if self.is_file else self.path / f'{directive}.json'
        data = util.read_from_possibly_empty(path)

        if self.is_file:
            data = data[directive]

        return data

    def dump(self, directive: str, *, data: List[Dict[str, Any]]) -> None:
        path = self.path if self.is_file else self.path / f'{directive}.json'
        
        if self.is_file:
            existing_data = util.read_from_possibly_empty(path)
            existing_data[directive] = data
            data = existing_data.copy()

        with path.open('w') as j:
            json.dump(data, j, indent=4)
