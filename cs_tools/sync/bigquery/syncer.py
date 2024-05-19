from __future__ import annotations

from typing import Union
import datetime as dt
import logging
import pathlib
import uuid

from google.cloud import bigquery
from sqlalchemy_bigquery._helpers import create_bigquery_client
import pydantic
import sqlalchemy as sa

from cs_tools import __version__
from cs_tools.sync.base import DatabaseSyncer
from cs_tools.sync.types import TableRows

from . import sanitize

log = logging.getLogger(__name__)


class BigQuery(DatabaseSyncer):
    """Interact with a BigQuery database."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "BigQuery"

    project_id: str
    dataset: str
    credentials_keyfile: pydantic.FilePath

    _bq: bigquery.Client = None

    @property
    def bq(self) -> bigquery.Client:
        """Get the underlying BigQuery client."""
        assert self._bq is not None
        return self._bq

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.create_engine(self.make_url(), connect_args={"client": self.bq}, future=True)

    def __repr__(self):
        return f"<BigQuerySyncer to {self.project_id}/{self.dataset}>"

    def make_url(self) -> str:
        """Create a connection string for the BigQuery JDBC driver."""
        job_config = bigquery.QueryJobConfig()
        job_config.default_dataset = f"{self.project_id}.{self.dataset}"
        job_config.labels = {"query_client": f"thoughtspot_cs_tools_v{__version__.replace('.', '-')}"}

        self._bq = create_bigquery_client(
            credentials_path=self.credentials_keyfile,
            default_query_job_config=job_config,
            project_id=self.project_id,
        )

        return f"bigquery://{self.project_id}/{self.dataset}?credentials_path={self.credentials_keyfile}"

    def copy_into(self, *, data: TableRows, into: Union[sa.Table, str], wait: bool = False) -> None:
        """Implement a COPY INTO statement using the BigQuery API."""
        table = self.bq.get_table(f"{self.project_id}.{self.dataset}.{into}")
        data = sanitize.clean_for_bq(data)

        config = bigquery.LoadJobConfig(schema=table.schema)
        job = self.bq.load_table_from_json(data, table, job_config=config)
        log.debug(f"BigQuery {job.job_type.upper()} job started: {job.job_id} (>> {job.destination})")

        if wait:
            job.result()

    def merge_into(self, *, data: TableRows, into: sa.Table) -> None:
        """Implement a MERGE INTO statement using the BigQuery API."""
        temporary_stage_name = f"TMP_TABLE_{into}_{uuid.uuid4().hex[:5]}"
        temporary_stage = self.bq.create_table(
            table=bigquery.Table(
                table_ref=f"{self.project_id}.{self.dataset}.{temporary_stage_name}",
                schema=self.bq.get_table(f"{self.project_id}.{self.dataset}.{into}").schema,
            )
        )

        # SET EXPIRY
        temporary_stage.expires = dt.datetime.now(tz=dt.timezone.utc) + dt.timedelta(hours=1)
        self.bq.update_table(table=temporary_stage, fields=["expires"])

        # PUT (from in-memory)
        self.copy_into(data=data, into=temporary_stage_name, wait=True)

        # MERGE INTO
        joins = [f"SOURCE.{c.name} = TARGET.{c.name}" for c in into.primary_key]

        joined = " AND ".join(joins)
        update = ", ".join(f"TARGET.{c.name} = SOURCE.{c.name}" for c in into.columns if c.name not in into.primary_key)
        insert = ", ".join(c.name for c in into.columns)
        values = ", ".join(f"SOURCE.{c.name}" for c in into.columns)

        # fmt: off
        SQL_MERGE_INTO = (
            f"""
            MERGE `{self.dataset}.{into}`  AS TARGET
            USING `{self.dataset}.{temporary_stage_name}` AS SOURCE
               ON {joined}
             WHEN     MATCHED THEN UPDATE SET {update}
             WHEN NOT MATCHED THEN INSERT ({insert}) VALUES ({values})
            """
        )
        # fmt: on

        job = self.bq.query(SQL_MERGE_INTO)
        log.debug(f"BigQuery {job.job_type.upper()} job started: {job.job_id} (>> {job.destination})")

    def load(self, tablename: str) -> TableRows:
        """SELECT rows from BigQuery."""
        table = self.metadata.tables[tablename]
        rows = self.session.execute(table.select())
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: TableRows) -> None:
        """INSERT rows into BigQuery."""
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        table = self.metadata.tables[tablename]

        if self.load_strategy == "APPEND":
            self.copy_into(data=data, into=table)

        if self.load_strategy == "TRUNCATE":
            self.session.execute(table.delete().where(True))  # type: ignore
            self.copy_into(data=data, into=table)

        if self.load_strategy == "UPSERT":
            self.merge_into(data=data, into=table)
