from __future__ import annotations

from typing import Literal
import logging
import pathlib

import sqlalchemy as sa

from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import DatabaseSyncer
from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class Redshift(DatabaseSyncer):
    """Interact with a Redshift Database."""

    __manifest_path__ = pathlib.Path(__file__).parent
    __syncer_name__ = "Redshift"

    host: str
    port: int = 5439
    username: str
    password: str
    database: str
    authentication: Literal["basic"] = "basic"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.create_engine(self.make_url(), future=True)

    def make_url(self) -> str:
        """Create a connection string for the Redshift JDBC driver."""
        host = self.host
        port = self.port
        username = self.username
        password = self.password
        database = self.database
        return f"redshift+psycopg2://{username}:{password}@{host}:{port}/{database}"

    def __repr__(self):
        return f"<RedshiftSyncer to {self.host}/{self.database}>"

    def load(self, tablename: str) -> TableRows:
        """SELECT rows from Redshift."""
        table = self.metadata.tables[tablename]
        rows = self.session.execute(table.select())
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: TableRows) -> None:
        """INSERT rows into Redshift."""
        if not data:
            log.warning(f"No data to write to syncer {self}")
            return

        table = self.metadata.tables[tablename]

        if self.load_strategy == "APPEND":
            sync_utils.batched(table.insert().values, session=self.session, data=data, max_parameters=250)
            self.session.commit()

        if self.load_strategy == "TRUNCATE":
            self.session.execute(table.delete())
            sync_utils.batched(table.insert().values, session=self.session, data=data, max_parameters=250)

        if self.load_strategy == "UPSERT":
            # TODO: @saurabhsingh1608, 2024/04/09
            #   need to investigate COPY->MERGE INTO functionality, similar to how we have in Snowflake syncer
            #   https://docs.aws.amazon.com/redshift/latest/dg/r_MERGE.html
            #
            sync_utils.generic_upsert(table, session=self.session, data=data, max_params=250)
