from __future__ import annotations

import pydantic
import sqlalchemy as sa
import sqlmodel
from cs_tools.sync.base import DatabaseSyncer
from typing import TYPE_CHECKING, Any, Literal ,Optional
import pathlib
import logging
from cs_tools import __version__
from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import DatabaseSyncer

# if TYPE_CHECKING:
from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class Postgres(DatabaseSyncer):
    """
    Interact with Postgres Database
    """
    
    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "postgres"
   
    database: str 
    username:  str 
    secret:  Optional[str] = None 
    host:  str 
    port: Optional[int] = pydantic.Field(default=5432)
    schema_ : str = pydantic.Field(default="PUBLIC",alias="schema")
    
    # authentication needs to be implemented 
    log_level: Literal["debug", "info", "warning"] = "warning"
    @pydantic.field_validator("secret", mode="before") 
    
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self._engine = sa.create_engine(self.make_url())
        self.metadata = sqlmodel.MetaData(schema=self.schema_)

    def __repr__(self) -> str:
        database = self.database
        username = self.username
        host = self.host
        port = self.port
        return f"<PostgresSyncer DATABASE='{database}', USER='{username}', HOST='{host}', PORT='{port}'>"
    
    def make_url(self):
        """Create a connection string for the Postgres JDBC driver."""
        auth = self.username if self.password is None else f"{self.username}:{self.password}"
        return f"postgresql+psycopg2://{auth}@{self.host}/{self.dbname}"
    
    # MANDATORY PROTOCOL MEMBERS
    
    
    def load(self, tablename: str, batch_size: int = 1000) -> TableRows:
        """SELECT rows from Postgres SQL"""
        table = self.metadata.tables[f"{self.schema_}.{tablename}"]
        rows = self.session.execute(table.select())
        result = []
        for batch in self.batched(rows, batch_size):
            result.extend([row.model_dump() for row in batch])
        return result

    def batched(self, iterable, n):
        """Yield successive n-sized chunks from iterable."""
        for i in range(0, len(iterable), n):
            yield iterable[i:i + n]
            
    # COPY_INTO method needs to be implemented. Work Around to be researched for the same.
    
            
    def dump(self, tablename: str, *, data: TableRows) -> None:
        """INSERT rows into Postgres SQL."""
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
            sync_utils.generic_upsert(table, session=self.session, data=data)

        self.session.commit()
        


   
   
   
   


