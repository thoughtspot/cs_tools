from __future__ import annotations

from typing import TYPE_CHECKING
import logging
import pathlib

import sqlalchemy as sa

from cs_tools.sync.base import DatabaseSyncer

if TYPE_CHECKING:
    from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class SQLite(DatabaseSyncer):
    """
    Interact with a SQLite database.
    """

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "sqlite"

    database_path: pathlib.Path

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.create_engine(f"sqlite:///{self.database_path}", future=True)
        self._connection = self._engine.connect()

    def __repr__(self):
        return f"<DatabaseSyncer ({self.name}) sync: conn_string='{self.engine.url}'>"

    # MANDATORY PROTOCOL MEMBERS

    def load(self, table: str) -> TableRows:
        """INSERT rows into SQLite."""
        t = self.metadata.tables[table]

        with self.connection.begin_nested():
            r = self.connection.execute(t.select())

        return [dict(_) for _ in r]

    def dump(self, table: str, *, data: TableRows) -> None:
        """SELECT rows from SQLite."""
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        t = self.metadata.tables[table]

        with self.connection.begin_nested():
            if self.truncate_on_load:
                self.connection.execute(t.delete())

            self.connection.execute(t.insert(), data)
