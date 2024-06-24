from __future__ import annotations

from typing import TYPE_CHECKING, Union
import logging
import pathlib

import pydantic
import sqlalchemy as sa

from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import DatabaseSyncer

from . import const

if TYPE_CHECKING:
    from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class SQLite(DatabaseSyncer):
    """Interact with a SQLite database."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "sqlite"

    database_path: Union[pydantic.FilePath, pydantic.NewPath]

    @pydantic.field_validator("database_path", mode="after")
    def ensure_endswith_db(cls, path: pathlib.Path) -> pathlib.Path:
        if path.suffix != ".db":
            raise ValueError("path must be a valid .db file")
        return path

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.create_engine(f"sqlite:///{self.database_path}", future=True)

    def __repr__(self):
        return f"<SQLiteSyncer conn_string='{self.engine.url}'>"

    # @contextlib.contextmanager
    # def pragma_speedy_insert(self):
    #     """ """
    #     self.session.execute("PRAGMA journal_mode = OFF;")
    #     self.session.execute("PRAGMA synchronous = 0;")
    #     self.session.execute("PRAGMA locking_mode = EXCLUSIVE;")
    #     self.session.execute("PRAGMA temp_store = MEMORY;")
    #     yield
    #     self.session.execute("PRAGMA journal_mode = ON;")
    #     self.session.execute("PRAGMA synchronous = 0;")
    #     self.session.execute("PRAGMA locking_mode = EXCLUSIVE;")
    #     self.session.execute("PRAGMA temp_store = MEMORY;")

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tablename: str) -> TableRows:
        """SELECT rows from SQLite."""
        table = self.metadata.tables[tablename]
        rows = self.session.execute(table.select())
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: TableRows) -> None:
        """INSERT rows into SQLite."""
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        table = self.metadata.tables[tablename]

        if self.load_strategy == "APPEND":
            sync_utils.batched(
                table.insert().values, session=self.session, data=data, max_parameters=const.SQLITE_MAX_VARIABLES
            )

        if self.load_strategy == "TRUNCATE":
            self.session.execute(table.delete())
            sync_utils.batched(
                table.insert().values, session=self.session, data=data, max_parameters=const.SQLITE_MAX_VARIABLES
            )

        if self.load_strategy == "UPSERT":
            sync_utils.generic_upsert(table, session=self.session, data=data)

        self.session.commit()
