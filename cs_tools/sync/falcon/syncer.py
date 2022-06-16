from typing import Any, Dict, List
import tempfile
import logging
import csv

from pydantic.dataclasses import dataclass
from pydantic import Field
import sqlalchemy as sa
import httpx
import click

from cs_tools.errors import SyncerError, ThoughtSpotUnreachable, TSLoadServiceUnreachable
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
    timeout: float = 60.0
    ignore_load_balancer_redirect: bool = False

    # DATABASE ATTRIBUTES
    __is_database__ = True

    def __post_init_post_parse__(self):
        self.timeout = self.timeout or None
        ctx = click.get_current_context()
        self.engine = sa.engine.create_mock_engine('sqlite://', self.intercept_create_table)
        self.cnxn = self.engine.connect()
        self._thoughtspot = getattr(ctx.obj, 'thoughtspot', None)

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

        self.ts.tql.command(
            command=f'{q};',
            database=self.database,
            http_timeout=self.timeout
        )

    def ensure_setup(self, metadata, cnxn, **kw):

        if self.ts is None:
            # DEV NOTE:
            # I think we can realistically only reach here if Falcon is meant to be
            # active AND we are attempting to run a tools command, so that's not the 
            # case, @boonhapus has gotta take a better look.
            raise ThoughtSpotUnreachable('unknown reason')

        if self.ts.platform.deployment == 'cloud':
            raise SyncerError(
                'Falcon is not available for data load operations on TS Cloud '
                'deployments'
            )

        # create the database and schema if it doesn't exist
        self.ts.tql.command(
            command=f'CREATE DATABASE {self.database};', http_timeout=self.timeout
        )

        self.ts.tql.command(
            command=f'CREATE SCHEMA {self.database}.{self.schema_};',
            http_timeout=self.timeout
        )

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
        r = self.ts.tql.query(
            statement=f'{q};',
            database=self.database,
            http_timeout=self.timeout
        )
        d = next(_['data'] for _ in r if 'data' in _)  # there will be only 1 response
        return d

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
                    ignore_node_redirect=self.ignore_load_balancer_redirect,
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
