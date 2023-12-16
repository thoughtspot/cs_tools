from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional
import json
import logging
import pathlib

import pydantic

from cs_tools.sync.base import Syncer

if TYPE_CHECKING:
    from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class JSON(Syncer):
    """Interact with a JSON file."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "sqlite"

    directory: pydantic.DirectoryPath
    encoding: Optional[Literal["UTF-8"]] = None

    def __repr__(self):
        return f"<JSONSyncer directory={self.directory.as_posix()}'>"

    def make_filename(self, filename: str) -> pathlib.Path:
        """Enforce the JSON extension."""
        return self.directory / f"{filename}.json"

    # MANDATORY PROTOCOL MEMBERS

    def load(self, filename: str) -> TableRows:
        """Fetch rows from a JSON file."""
        text = self.make_filename(filename).read_text(encoding=self.encoding)

        if not text:
            return []

        data = json.loads(text)
        return data

    def dump(self, filename: str, *, data: TableRows) -> None:
        """Write rows to a JSON file."""
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        text = json.dumps(data, ensure_ascii=True if self.encoding is None else False)
        self.make_filename(filename).write_text(text, encoding=self.encoding)
