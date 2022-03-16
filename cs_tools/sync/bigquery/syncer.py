from typing import Any, Dict, List
import pathlib
import logging

from pydantic.dataclasses import dataclass
from google.cloud import bigquery
import sqlalchemy as sa

from . import sanitize


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
    credentials_file: pathlib.Path = None
    truncate_on_connect: bool = True

    # DATABASE ATTRIBUTES
    __is_database__ = True
    metadata = None

    @property
    def bq(self) -> bigquery.Client:
        """
        Get the underlying BigQuery client.
        """
        return self.cnxn.connection._client

    def __post_init_post_parse__(self):
        engine_kw = {}

        if self.credentials_file is not None:
            engine_kw['credentials_path'] = self.credentials_file

        self.engine = sa.create_engine(f'bigquery://{self.project_name}/{self.dataset}', **engine_kw)
        self.cnxn = self.engine.connect()

        # decorators must be declared here, SQLAlchemy doesn't care about instances
        sa.event.listen(sa.schema.MetaData, 'after_create', self.capture_metadata)

    def capture_metadata(self, metadata, cnxn, **kw):
        self.metadata = metadata

        if self.truncate_on_connect:
            with self.cnxn.begin():
                for table in reversed(self.metadata.sorted_tables):
                    self.cnxn.execute(table.delete().where(True))

    def __repr__(self):
        return f"<Database (bigquery) sync: conn_string='{self.engine.url}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return 'bigquery'

    def load(self, table: str) -> List[Dict[str, Any]]:
        t = self.metadata.tables[table]

        with self.cnxn.begin():
            r = self.cnxn.execute(t.select())

        return [dict(_) for _ in r]

    def dump(self, table: str, *, data: List[Dict[str, Any]]) -> None:
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
        t = self.bq.get_table(f'{self.project_name}.{self.dataset}.{table}')
        d = sanitize.clean_for_bq(data)
        r = self.bq.insert_rows_json(t, d)

        for error in r:
            log.warning(f'ERROR FROM BIGQUERY:\n{error}')