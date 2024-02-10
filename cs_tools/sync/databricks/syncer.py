from __future__ import annotations
from typing import Any, AnyStr, Dict, List, Optional
import logging
import pathlib
import pydantic

import sqlalchemy as sa
import sqlmodel

from cs_tools import __version__
from cs_tools.sync.base import DatabaseSyncer
from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)



class Databricks(DatabaseSyncer):
    """
    Interact with a Databricks database.

    SSL Error [Mac OS]: Install Certificates -> /Applications/Python x.y/Install Certificates.command
    -> Check if mac

    1. Insert Many Pattern for Databricks
    2. Dialects-> max variable in single statment
    
    """
    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "Databricks"

    access_token: str
    server_hostname: str
    http_path: str
    catalog: str
    schema_: str = pydantic.Field(default="default", alias="schema")
    port: Optional[str] = 443

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connection_string = (
                    "databricks://token:{token}@{host}:{port}?http_path={http_path}&catalog={database}&schema={db_schema}".format(
                                        token=self.access_token,
                                        host=self.server_hostname,
                                        port=self.port,
                                        database=self.catalog,
                                        http_path=self.http_path,
                                        db_schema=self.schema_))
        self._engine=sa.create_engine(self.connection_string)
        self.metadata = sqlmodel.MetaData(schema=self.schema_)


    @pydantic.field_validator("access_token",mode="before")
    @classmethod
    def ensure_dapi_prefix(cls,value: Any) -> str:
        if not str(value).startswith("dapi"):
            raise ValueError("Token should start with 'dapi'")
        return value

        

    def load(self, tablename: str) -> TableRows:  
        """SELECT rows from Databricks"""
        table = self.metadata.tables[f"{self.schema_}.{tablename}"]
        rows = self.session.execute(table.select())
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: TableRows) -> None:
        

        table = self.metadata.tables[f"{self.schema_}.{tablename}"]
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
            raise NotImplementedError('Not Done...')





      
    