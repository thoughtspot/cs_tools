from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Union
import logging
import pathlib

from sqlalchemy.dialects.sqlite import insert
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
    pragma_speedy_inserts: bool = False

    @pydantic.field_validator("database_path", mode="after")
    def ensure_endswith_db(cls, path: pathlib.Path) -> pathlib.Path:
        if path.suffix != ".db":
            raise ValueError("path must be a valid .db file")
        return path

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.create_engine(f"sqlite:///{self.database_path}", future=True)

    def __finalize__(self):
        super().__finalize__()

        if self.pragma_speedy_inserts:
            # CONTINUES WITHOUT SYNCING ONCE DATA IS HANDED OFF TO THE OS, PROGRAM MAY CRASHES CORRUPT THE DATABASE.
            self.session.execute(sa.text("PRAGMA synchronous = OFF;"))
            # MAINTAIN THE LOCK ON THE SQLITE DATABASE FILE. DON'T RELEASE/ACQUIRE IT.
            self.session.execute(sa.text("PRAGMA locking_mode = EXCLUSIVE;"))
            # STORE TEMPORARY TABLES AND VIEWS IN RAM.
            self.session.execute(sa.text("PRAGMA temp_store = MEMORY;"))

    def __repr__(self):
        return f"<SQLiteSyncer conn_string='{self.engine.url}'>"

    def read_stream(self, tablename: str, *, batch: int = 100_000) -> Iterator[TableRows]:
        """Read rows from a SQLite database."""
        table = self.metadata.tables[tablename]

        with self.session.execute(table.select()).yield_per(num=batch) as result:
            for rows in result.partitions():
                yield [row._asdict() for row in rows]

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tablename: str) -> TableRows:
        """SELECT rows from SQLite."""
        table = self.metadata.tables[tablename]
        query = table.select()
        result = self.session.execute(query)
        rows = [row._asdict() for row in result.all()]
        return rows

    def dump(self, tablename: str, *, data: TableRows) -> None:
        """INSERT rows into SQLite."""
        if not data:
            log.warning(f"no '{tablename}' data to write to syncer {self}")
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
            sync_utils.batched(
                insert(table).prefix_with("OR REPLACE").values,
                session=self.session,
                data=data,
                max_parameters=const.SQLITE_MAX_VARIABLES,
           )

        self.session.commit()
