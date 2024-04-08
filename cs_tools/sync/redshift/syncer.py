from typing import Any, Optional
import logging
import pathlib

import pydantic
import redshift_connector
import sqlalchemy as sa
from sqlalchemy.engine.url import URL
import sqlmodel

from cs_tools.sync.base import DatabaseSyncer
from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)

class Redshift(DatabaseSyncer):

    """
    Interact with Redshift DataBase
    """
    __manifest_path__ = pathlib.Path(__file__).parent
    __syncer_name__   = "Redshift"

    host : str
    database : str
    user : str
    password : str
    port : int
    username : str
    password : str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(kwargs)
        self.engine_url=URL.create(
                        drivername='redshift+psycopg2', # indicate redshift_connector driver and dialect will be used
                        host=self.host,
                        port=self.port,
                        database=self.database, # Amazon Redshift database
                        username=self.user, # Okta username
                        password=self.password # Okta password
                        )
        self._engine = sa.create_engine(self.engine_url)
        # self.metadata = sqlmodel.MetaData(schema=self.schema_)

    
    def load(self, tablename: str) -> TableRows:  
        """SELECT rows from Redshift"""
        table = self.metadata.tables[f"{tablename}"]
        rows = self.session.execute(table.select())
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: TableRows) -> None:
        

        table = self.metadata.tables[f"{tablename}"]
        if not data:
            log.warning(f"No data to write to syncer {table}")
            return
        
        if self.load_strategy == "APPEND":
            self.session.execute(table.insert(), data)
            self.session.commit()

        if self.load_strategy == "TRUNCATE":
            self.session.execute(table.delete())
            self.session.execute(table.insert(), data)

        if self.load_strategy == "UPSERT":
            raise NotImplementedError("Not Done...")
