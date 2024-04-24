from __future__ import annotations

import pydantic
import sqlalchemy as sa
import sqlmodel
from cs_tools.sync.base import DatabaseSyncer
from typing import TYPE_CHECKING, Any, Literal ,Optional
from pydantic_core import PydanticCustomError
import pathlib
import logging
from sqlalchemy.orm import sessionmaker
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
   
    dbname: str 
    user:  str 
    password:  str 
    host:  str 
    port: int 
    schema_ : str = pydantic.Field(default="PUBLIC",alias="schema")
    authentication: Literal["basic", "key-pair", "sso", "oauth"]
    log_level: Literal["debug", "info", "warning"] = "warning"
    secret: Optional[str] = None
    private_key_path: Optional[pydantic.FilePath] = None
        
    @pydantic.field_validator("secret", mode="before")
    def ensure_auth_secret_given(cls, value: Any, info: pydantic.ValidationInfo) -> Any:
        if info.data.get("authentication") == "sso" or value is not None:
            return value

        if info.data.get("authentication") == "basic":
            raise PydanticCustomError("missing", "Field required, you must provide a password", {"secret": value})

        if info.data.get("authentication") == "oauth":
            raise PydanticCustomError("missing", "Field required, you must provide an oauth token", {"secret": value})
    
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logging.getLogger("postgres").setLevel(self.log_level.upper())
        
        self._engine = sa.create_engine(self.make_url())
        self.Session = sessionmaker(bind=self.engine)
        self.metadata = sqlmodel.MetaData(schema=self.schema_)

    def __repr__(self) -> str:
        database = self.dbname
        username = self.user
        host = self.host
        port = self.port
        return f"<PostgresSyncer DATABASE='{database}', USER='{username}', HOST='{host}', PORT='{port}'>"
    
    def make_url(self):
        """Create a connection string for the Postgres JDBC driver."""
        dialect = "postgresql"
        driver = "psycopg2"
        connection_string = f"{dialect}+{driver}://{self.user}:{self.password}@{self.host}/{self.dbname}"
        return connection_string
    
    # MANDATORY PROTOCOL MEMBERS
    
    @staticmethod
    def output_to_list(rows):
        output_list = []
        for row in rows:
            values = [str(value) for value in row]
            output_list.append(values)
        return output_list
    
    def load(self, tablename: str) -> TableRows:
        """SELECT rows from Postgresql SQL."""
        table = self.metadata.tables[f"{self.schema_}.{tablename}"]
        rows = self.session.execute(table.select())
        result = self.output_to_list(rows) 
        return result

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
        


   
   
   
   


