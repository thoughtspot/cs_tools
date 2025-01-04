from __future__ import annotations

import logging
import pathlib

import sqlalchemy as sa

from cs_tools import _types
from cs_tools.sync.base import DatabaseSyncer

log = logging.getLogger(__name__)


class Mock(DatabaseSyncer):
    """Pretend to interact with a particular syncer."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "mock"

    # dialect: Literal["Databricks", "Falcon", "Redshift", "Snowflake", "SQLite", "Starburst", "Trino"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.engine.create_mock_engine("sqlite://", self.sql_query_to_log)  # type: ignore[assignment]

    def __finalize__(self) -> None:
        log.warning("[fg-warn]THESE DDL ARE APPROXIMATE, YOU WILL NEED TO CUSTOMIZE TO YOUR DIALECT.")
        super().__finalize__()
        log.info("ALL SCOPED TABLES HAVE BEEN PRINTED, EXITING..")
        raise SystemExit(-1)

    def sql_query_to_log(self, query: sa.schema.ExecutableDDLElement, *_multiparams, **_params):
        """Convert a SQL query into a string."""
        compiled = query.compile(dialect=self.engine.dialect)
        log.info(f"\n{compiled.string.strip()}\n")

    def __repr__(self):
        # return f"<Mock{self.dialect.title()}Syncer>"
        return "<MockSyncer>"

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tablename: str):
        pass

    def dump(self, tablename: str, *, data: _types.TableRowsFormat):
        pass
