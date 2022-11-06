from typing import Any, Dict, List
import pathlib
import logging

from pydantic.dataclasses import dataclass
import sqlalchemy as sa


log = logging.getLogger(__name__)


@dataclass
class SQLite:
    """
    Interact with a SQLite database.
    """
    database_path: pathlib.Path
    truncate_on_load: bool = True

    # DATABASE ATTRIBUTES
    __is_database__ = True

    def __post_init_post_parse__(self):
        self.database_path = path = self.database_path.resolve()
        self.engine = sa.create_engine(f'sqlite:///{path}', future=True)
        self.cnxn = self.engine.connect()

        # decorators must be declared here, SQLAlchemy doesn't care about instances
        sa.event.listen(sa.schema.MetaData, 'after_create', self.capture_metadata)

    def capture_metadata(self, metadata, cnxn, **kw):
        self.metadata = metadata

    def __repr__(self):
        return f"<Database ({self.name}) sync: conn_string='{self.engine.url}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return 'sqlite'

    def load(self, table: str) -> List[Dict[str, Any]]:
        t = self.metadata.tables[table]

        with self.cnxn.begin_nested():
            r = self.cnxn.execute(t.select())

        return [dict(_) for _ in r]

    def dump(self, table: str, *, data: List[Dict[str, Any]]) -> None:
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        t = self.metadata.tables[table]

        with self.cnxn.begin_nested():
            if self.truncate_on_load:
                self.cnxn.execute(t.delete())

            self.cnxn.execute(t.insert(), data)
