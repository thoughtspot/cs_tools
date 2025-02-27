from __future__ import annotations

from typing import cast
import logging
import pathlib

import sqlalchemy as sa

from cs_tools import _types
from cs_tools.sync.base import DatabaseSyncer

_LOG = logging.getLogger(__name__)


class Mock(DatabaseSyncer):
    """Pretend to interact with a particular syncer."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "mock"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = cast(sa.engine.Engine, sa.engine.create_mock_engine("sqlite://", self.sql_query_to_log))

    def __finalize__(self) -> None:
        _LOG.warning("[fg-warn]THESE ARE [fg-secondary]SQLITE[/] DDL, YOU WILL NEED TO CUSTOMIZE TO YOUR DIALECT.")
        super().__finalize__()
        _LOG.info("ALL SCOPED TABLES HAVE BEEN PRINTED, EXITING..")
        raise SystemExit(-1)

    def sql_query_to_log(self, sql: sa.sql.ClauseElement, *_multiparams, **_params) -> None:
        """Convert a SQL query into a string."""
        compiled = sql.compile(dialect=self.engine.dialect)
        _LOG.info(f"\n{compiled.string.strip()}\n")

    def __repr__(self):
        return "<MockSyncer dialect='sqlite'>"

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tablename: str) -> _types.TableRowsFormat:
        raise NotImplementedError(f"{self} doesn't support data loading.")

    def dump(self, tablename: str, *, data: _types.TableRowsFormat):
        raise NotImplementedError(f"{self} doesn't support data dumping.")
