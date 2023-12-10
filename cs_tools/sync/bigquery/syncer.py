from __future__ import annotations

from typing import TYPE_CHECKING, Any
import logging

from google.cloud import bigquery
from pydantic.dataclasses import dataclass
import sqlalchemy as sa

from . import sanitize

if TYPE_CHECKING:
    import pathlib

log = logging.getLogger(__name__)


@dataclass
class BigQuery:
    """
    Interact with a BigQuery database.

    - Select or create a Cloud Platform project.
    - [Optional] Enable billing for your project.
    - Enable the BigQuery Storage API.
    - Setup Authentication.
    """

    project_name: str
    dataset: str
    credentials_file: pathlib.Path
    truncate_on_load: bool = True

    # DATABASE ATTRIBUTES
    __is_database__ = True

    @property
    def bq(self) -> bigquery.Client:
        """
        Get the underlying BigQuery client.
        """
        return self.cnxn.connection._client

    def __post_init_post_parse__(self):
        self.engine = sa.create_engine(
            f"bigquery://{self.project_name}/{self.dataset}", credentials_path=self.credentials_file
        )

        self.cnxn = self.engine.connect()

        # decorators must be declared here, SQLAlchemy doesn't care about instances
        sa.event.listen(sa.schema.MetaData, "after_create", self.capture_metadata)

    def capture_metadata(self, metadata, cnxn, **kw):
        self.metadata = metadata

    def __repr__(self):
        return f"<Database ({self.name}) sync: conn_string='{self.engine.url}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return "bigquery"

    def load(self, table: str) -> list[dict[str, Any]]:
        t = self.metadata.tables[table]

        with self.cnxn.begin():
            r = self.cnxn.execute(t.select())

        return [dict(_) for _ in r]

    def dump(self, table: str, *, data: list[dict[str, Any]]) -> None:
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        t = self.metadata.tables[table]

        if self.truncate_on_load:
            with self.cnxn.begin():
                self.cnxn.execute(t.delete().where(True))

        # DEV NOTE: nicholas.cooper@thoughtspot.com
        #
        # Why are we using the underlying BigQuery client?
        #
        # IDK man, Google implemented their SQLAlchemy connector to do individual INSERT
        # queries when provided INSERT MANY orm syntax. I've ETL'd to BigQuery more than
        # often enough to simply just take advantage of the BigQuery client library
        # itself.
        #
        # BigQuery doesn't have a notion of PRIMARY KEY or UNIQUE CONSTRAINT anyway, so
        # transactions and rollback logic is not REALLY possible without more
        # orchestration.
        #
        t = self.bq.get_table(f"{self.project_name}.{self.dataset}.{table}")
        d = sanitize.clean_for_bq(data)

        cfg = bigquery.LoadJobConfig(schema=t.schema)
        self.bq.load_table_from_json(d, t, job_config=cfg)
