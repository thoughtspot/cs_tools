from __future__ import annotations

from typing import Optional
import logging
import pathlib

from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import DatabaseSyncer
from cs_tools.sync.types import TableRows
import pydantic
import sqlalchemy as sa
import sqlmodel

log = logging.getLogger(__name__)


class Postgres(DatabaseSyncer):
    """Interact with Postgres database."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "postgres"

    host: str
    port: Optional[int] = pydantic.Field(default=5432)
    database: str
    schema_: str = pydantic.Field(default="public", alias="schema")
    username: str
    secret: Optional[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.create_engine(self.make_url(), future=True)
        self.metadata = sqlmodel.MetaData(schema=self.schema_)

    def __repr__(self) -> str:
        return f"<PostgresSyncer {self.host}/{self.database}>"

    def make_url(self) -> str:
        """Create a connection string for the Postgres JDBC driver."""
        auth = f"{self.username}:{self.secret}" if self.secret is not None else self.username
        return f"postgresql+psycopg2://{auth}@{self.host}:{self.port}/{self.database}"

    def load(self, tablename: str) -> TableRows:
        """SELECT rows from PostgreSQL."""
        table = self.metadata.tables[f"{self.schema_}.{tablename}"]
        rows = self.session.execute(table.select())
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: TableRows) -> None:
        """INSERT rows into PostgreSQL."""
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        table = self.metadata.tables[f"{self.schema_}.{tablename}"]

        if self.load_strategy == "APPEND":
            sync_utils.batched(table.insert().values, session=self.session, data=data)

        if self.load_strategy == "TRUNCATE":
            self.session.execute(table.delete())
            sync_utils.batched(table.insert().values, session=self.session, data=data)

        if self.load_strategy == "UPSERT":
            # TODO: @dhinesh-ts, 2024/05/19
            #   need to investigate COPY->INSERT ON CONFLICT functionality, similar to how we have in Snowflake syncer
            #   https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#insert-on-conflict-upsert
            #
            sync_utils.generic_upsert(table, session=self.session, data=data)
