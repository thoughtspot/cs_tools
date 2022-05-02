from typing import Any, Dict, List
import tempfile
import logging
import csv

from pydantic.dataclasses import dataclass
from pydantic import Field
import sqlalchemy as sa
import httpx
import click

from cs_tools.errors import TSLoadServiceUnreachable
from . import compiler, sanitize


log = logging.getLogger(__name__)


@dataclass
class Falcon:
    """
    Interact with Falcon.
    """
    database: str = 'cs_tools'
    schema_: str = Field('falcon_default_schema', alias='schema')
    empty_target: bool = True

    # DATABASE ATTRIBUTES
    __is_database__ = True
    metadata = None

    def __post_init_post_parse__(self):
        ctx = click.get_current_context()
        self.engine = sa.engine.create_mock_engine('sqlite://', self.intercept_create_table)
        self.cnxn = self.engine.connect()
        self._thoughtspot = getattr(ctx.obj, 'thoughtspot', '')

        # decorators must be declared here, SQLAlchemy doesn't care about instances
        sa.event.listen(sa.schema.MetaData, 'before_create', self.ensure_setup)
        sa.event.listen(sa.schema.MetaData, 'after_create', self.capture_metadata)

    @property
    def ts(self):
        return self._thoughtspot

    def intercept_create_table(self, sql, *multiparams, **params):
        q = sql.compile(dialect=self.engine.dialect)
        q = str(q).strip()

        # ignore CREATE TABLE for ts_bi_server.. since this is Falcon, it exists already
        if 'ts_bi_server' in q:
            return

        self.ts.tql.command(command=f'{q};', database=self.database)

    def ensure_setup(self, metadata, cnxn, **kw):
        # create the database and schema if it doesn't exist
        self.ts.tql.command(command=f'CREATE DATABASE {self.database};')
        self.ts.tql.command(command=f'CREATE SCHEMA {self.database}.{self.schema_};')

    def capture_metadata(self, metadata, cnxn, **kw):
        self.metadata = metadata

    def __repr__(self):
        return f"<Database ({self.name}) sync>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return 'falcon'

    def load(self, table: str) -> List[Dict[str, Any]]:
        t = self.metadata.tables[table]
        q = t.select().compile(dialect=self.engine.dialect)
        q = str(q).strip()
        r = self.ts.tql.query(statement=f'{q};', database=self.database)
        return r

    def dump(self, table: str, *, data: List[Dict[str, Any]]) -> None:
        if not data:
            return

        data = sanitize.clean_for_falcon(data)

        file_opts = {
            'mode': 'w+',
            'encoding': 'utf-8',
            'newline': '',
            'dir': self.ts.config.temp_dir
        }

        with tempfile.NamedTemporaryFile(**file_opts) as fd:
            writer = csv.DictWriter(fd, data[0].keys(), delimiter='|')
            # writer.writeheader()
            writer.writerows(data)
            fd.seek(0)
            try:
                self.ts.tsload.upload(
                    fd,
                    database=self.database,
                    table=table,
                    empty_target=self.empty_target
                )
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                h = self.ts.api.ts_dataservice._tsload_node
                p = self.ts.api.ts_dataservice._tsload_port
                m = f'could not connect at [blue]{h}:{p}[/]'

                if h != self.ts.config.thoughtspot.host:
                    m += (
                        '\n\n[yellow]If that url is surprising to you, you likely have '
                        'the tsload service load balancer turned on (the default '
                        'setting) and the local machine cannot directly send files to '
                        'that node.\n\nConsider turning on your VPN or working with a '
                        'ThoughtSpot Support Engineer to disable the etl_http_server '
                        '(tsload connector service) load balancer.'
                    )
                raise TSLoadServiceUnreachable(m, http_error=e)
