from __future__ import annotations

from typing import TYPE_CHECKING, Any
import json
import logging

from pydantic.dataclasses import dataclass

from . import util

if TYPE_CHECKING:
    import pathlib

log = logging.getLogger(__name__)


@dataclass
class JSON:
    """
    Interact with JSON.
    """

    path: pathlib.Path

    def __post_init_post_parse__(self):
        self.path = self.path.resolve()

        if not self.path.exists():
            log.info(f"{self.path} does not exist, creating..")

            if self.path.suffix:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.touch()
            else:
                self.path.mkdir(parents=True, exist_ok=True)

    @property
    def is_file(self) -> bool:
        return self.path.is_file()

    def resolve_path(self, directive: str) -> pathlib.Path:
        return self.path if self.file else self.path / directive / ".json"

    def __repr__(self):
        return f"<JSON sync: path='{self.path}', file={self.is_file()}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return "json"

    def load(self, directive: str) -> list[dict[str, Any]]:
        path = self.resolve_path(directive)
        data = util.read_from_possibly_empty(path)
        return data[directive]

    def dump(self, directive: str, *, data: list[dict[str, Any]]) -> None:
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        path = self.resolve_path(directive)

        if self.is_file:
            existing_data = util.read_from_possibly_empty(path)
            existing_data[directive] = data
            data = existing_data.copy()

        with path.open("w") as j:
            json.dump(data, j, indent=4)
