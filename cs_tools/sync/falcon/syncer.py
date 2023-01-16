from __future__ import annotations
import tempfile
import logging
import csv

from pydantic.dataclasses import dataclass
from pydantic import Field
import sqlalchemy as sa
import httpx
import click
import io

from cs_tools.errors import TSLoadServiceUnreachable, SyncerError
from cs_tools.types import RecordsFormat

from . import sanitize, compiler

log = logging.getLogger(__name__)


@dataclass
class Falcon:
    """
    Interact with Falcon.
    """

    database: str = "cs_tools"
    schema_: str = Field("falcon_default_schema", alias="schema")
    empty_target: bool = True
    timeout: float = 60.0
    ignore_load_balancer_redirect: bool = False

    # DATABASE ATTRIBUTES
    __is_database__ = True

    def __post_init_post_parse__(self):
        ctx = click.get_current_context()
        self.timeout = None if self.timeout == 0 else self.timeout
        self.engine = sa.engine.create_mock_engine("sqlite://", self.intercept_create_table)
        self.cnxn = self.engine.connect()
        self._thoughtspot = getattr(ctx.obj, "thoughtspot", None)

        # decorators must be declared here, SQLAlchemy doesn't care about instances
        sa.event.listen(sa.schema.MetaData, "before_create", self.ensure_setup)
        sa.event.listen(sa.schema.MetaData, "after_create", self.capture_metadata)

    @property
    def ts(self):
        return self._thoughtspot

    def intercept_create_table(self, sql, *multiparams, **params):
        q = sql.compile(dialect=self.engine.dialect)
        q = str(q).strip()
        self.ts.tql.command(command=f"{q};", database=self.database, http_timeout=self.timeout)

    def ensure_setup(self, metadata, cnxn, **kw):

        if self.ts.platform.deployment == "cloud":
            raise SyncerError("Falcon is not available for data load operations on TS Cloud deployments")

        # create the database and schema if it doesn't exist
        self.ts.tql.command(command=f"CREATE DATABASE {self.database};", http_timeout=self.timeout)
        self.ts.tql.command(command=f"CREATE SCHEMA {self.database}.{self.schema_};", http_timeout=self.timeout)

    def capture_metadata(self, metadata, cnxn, **kw):
        self.metadata = metadata

    def __repr__(self):
        return f"<Database ({self.name}) sync>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return "falcon"

    def load(self, table: str) -> RecordsFormat:
        t = self.metadata.tables[table]
        q = t.select().compile(dialect=self.engine.dialect)
        q = str(q).strip()
        r = self.ts.tql.query(statement=f"{q};", database=self.database, http_timeout=self.timeout)
        d = next(_["data"] for _ in r if "data" in _)  # there will be only 1 response
        return d

    def dump(self, table: str, *, data: RecordsFormat) -> None:
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        data = sanitize.clean_for_falcon(data)

        file_opts = {"encoding": "utf-8", "newline": ""}

        with tempfile.NamedTemporaryFile(mode="wb+", dir=self.ts.config.temp_dir) as fd:
            with io.TextIOWrapper(fd, **file_opts) as txt:
                writer = csv.DictWriter(txt, data[0].keys(), delimiter="|")
                # writer.writeheader()
                writer.writerows(data)
                fd.seek(0)

                try:
                    self.ts.tsload.upload(
                        fd,
                        ignore_node_redirect=self.ignore_load_balancer_redirect,
                        database=self.database,
                        table=table,
                        empty_target=self.empty_target,
                        http_timeout=self.timeout,
                    )
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    r = f"could not connect at [b blue]{self.ts.api.dataservice_url}[/]"
                    m = ""

                    if self.ts.api.dataservice_url.host != self.ts.config.thoughtspot.host:
                        m = (
                            "Is your VPN connected?"
                            "\n\n"
                            "If that isn't the URL of your ThoughtSpot cluster, then your "
                            "ThoughtSpot admin likely has configured the Remote TSLoad "
                            "Connector Service to use a load balancer and your local "
                            "machine is unable to connect directly to the ThoughtSpot node "
                            "which is accepting files."
                            "\n\n"
                            "You can try using `[b blue]ignore_load_balancer_redirect[/]` "
                            "in your Falcon syncer definition as well."
                        )

                    raise TSLoadServiceUnreachable(reason=r, mitigation=m)
