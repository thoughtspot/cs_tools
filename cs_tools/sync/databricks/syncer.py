from __future__ import annotations

from typing import Any, Optional
import base64
import logging
import pathlib
import uuid

import httpx
import pydantic
import sqlalchemy as sa
import sqlmodel

from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import DatabaseSyncer
from cs_tools import _types

log = logging.getLogger(__name__)


class Databricks(DatabaseSyncer):
    """Interact with a Databricks database."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "Databricks"

    server_hostname: str
    http_path: str
    access_token: str
    catalog: str
    schema_: Optional[str] = pydantic.Field(default="default", alias="schema")
    port: Optional[int] = 443
    temp_dir: Optional[pydantic.DirectoryPath] = pathlib.Path(".")
    use_experimental_dataload: bool = False

    @pydantic.field_validator("access_token", mode="before")
    @classmethod
    def ensure_dapi_prefix(cls, value: Any) -> str:
        if not str(value).startswith("dapi"):
            raise ValueError("Access Token should start with 'dapi'")
        return value

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.create_engine(self.make_url(), future=True)
        self.metadata = sqlmodel.MetaData(schema=self.schema_)
        self.http_session = httpx.Client(base_url=self.server_hostname)
        self.http_session.headers["Authorization"] = f"Bearer {self.access_token}"

    def __repr__(self):
        return f"<DatabricksSyncer to {self.server_hostname}/{self.http_path}/{self.catalog}>"

    def make_url(self) -> str:
        """Create a connection string for the Databricks JDBC driver."""
        username = "token"
        password = self.access_token
        host = self.server_hostname
        port = self.port
        query = f"http_path={self.http_path}&catalog={self.catalog}&schema={self.schema_}"
        return f"databricks://{username}:{password}@{host}:{port}?{query}"

    def stage_and_put(self, tablename: str, *, data: _types.TableRowsFormat) -> str:
        """Add a local file to Databrick's internal temporary stage."""
        assert self.temp_dir is not None
        stage_name = f"TMP_STAGE_{tablename}_{uuid.uuid4().hex[:5]}.csv"

        # Further reading:
        #  https://docs.databricks.com/api/workspace/dbfs/create
        #  https://docs.databricks.com/api/workspace/dbfs/addblock
        #  https://docs.databricks.com/api/workspace/dbfs/close
        #

        r = self.http_session.post("api/2.0/dbfs/create", data={"path": f"/mnt/cs_tools/{stage_name}"})
        r.raise_for_status()

        remote_fh = r.json()["handle"]

        with sync_utils.temp_csv_for_upload(tmp=self.temp_dir, filename=tablename, data=data) as fd:
            ONE_MB = 1024 * 1024

            while block_raw := fd.read(ONE_MB):
                encoded = base64.b64encode(block_raw).decode("utf-8")
                r = self.http_session.post("api/2.0/dbfs/add-block", data={"handle": remote_fh, "data": encoded})
                r.raise_for_status()

        r = self.http_session.post("api/2.0/dbfs/close", data={"handle": remote_fh})
        r.raise_for_status()

        return stage_name

    def copy_into(self, *, into: str, from_: str) -> None:
        """Implement the COPY INTO statement."""
        #  https://docs.databricks.com/en/ingestion/copy-into/examples.html#load-csv-files-with-copy-into
        #

        # fmt: off
        SQL_COPY_INTO = sa.sql.text(
            f"""
            COPY INTO {into}
            FROM '/mnt/cs_tools/{from_}'
            FILEFORMAT = CSV
            FORMAT_OPTIONS (
                'mergeSchema' = 'true',
                'delimiter' = '|',
                'header' = 'true'
            )
            COPY_OPTIONS ('mergeSchema' = 'true')
            """
        )
        # fmt: on
        r = self.session.execute(SQL_COPY_INTO)
        log.debug("Databricks response >> COPY INTO\n%s", r.scalar())

    def load(self, tablename: str) -> _types.TableRowsFormat:
        """SELECT rows from Databricks"""
        table = self.metadata.tables[f"{self.schema_}.{tablename}"]
        rows = self.session.execute(table.select())
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: _types.TableRowsFormat) -> None:
        """INSERT rows into Databricks."""
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        table = self.metadata.tables[f"{self.schema_}.{tablename}"]

        if self.load_strategy == "APPEND":
            if self.use_experimental_dataload:
                stage = self.stage_and_put(tablename=tablename, data=data)
                self.copy_into(from_=stage, into=tablename)
            else:
                sync_utils.batched(table.insert().values, session=self.session, data=data, max_parameters=250)

        if self.load_strategy == "TRUNCATE":
            self.session.execute(table.delete())
            if self.use_experimental_dataload:
                stage = self.stage_and_put(tablename=tablename, data=data)
                self.copy_into(from_=stage, into=tablename)
            else:
                sync_utils.batched(table.insert().values, session=self.session, data=data, max_parameters=250)

        if self.load_strategy == "UPSERT":
            # TODO: @sameerjain901, 2024/02/10
            #   need to investigate COPY->MERGE INTO functionality, similar to how we have in Snowflake syncer
            #   https://docs.databricks.com/en/sql/language-manual/delta-merge-into.html
            #
            sync_utils.generic_upsert(table, session=self.session, data=data, max_params=250)
