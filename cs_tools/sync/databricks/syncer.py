from __future__ import annotations

from typing import Any, Optional
import logging
import pathlib

import pydantic
import sqlalchemy as sa
import sqlmodel

from cs_tools import __version__
from cs_tools.sync import utils as sync_utils
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

    server_hostname: str
    http_path: str
    access_token: str
    catalog: str
    schema_: Optional[str] = pydantic.Field(default="default", alias="schema")
    port: Optional[int] = 443

    @pydantic.field_validator("access_token", mode="before")
    @classmethod
    def ensure_dapi_prefix(cls,value: Any) -> str:
        if not str(value).startswith("dapi"):
            raise ValueError("Token should start with 'dapi'")
        return value

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.create_engine(self.make_url(), future=True)
        self.metadata = sqlmodel.MetaData(schema=self.schema_)

    def make_url(self) -> str:
        """Create a connection string for the Databricks JDBC driver."""
        url_kwargs = {
            "username": "token",
            "password": self.access_token,
            "host": self.server_hostname,
            "port": self.port,
            "query": f"http_path={self.http_path}&catalog={self.catalog}&schema={self.schema_}",
        }
        return "databricks://{username}:{password}@{host}:{port}?{query}".format(**url_kwargs)

    def __repr__(self):
        return f"<DatabricksSyncer to {self.server_hostname}/{self.http_path}/{self.catalog}>"

    def load(self, tablename: str) -> TableRows:  
        """SELECT rows from Databricks"""
        table = self.metadata.tables[f"{self.schema_}.{tablename}"]
        rows = self.session.execute(table.select())
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: TableRows) -> None:
        """INSERT rows into Databricks."""
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
