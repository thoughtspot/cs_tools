from __future__ import annotations

from typing import TYPE_CHECKING, Any
import logging
import pathlib

import httpx
import pydantic
import sqlalchemy as sa

from cs_tools import errors
from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import DatabaseSyncer
from cs_tools.thoughtspot import ThoughtSpot

from . import (
    compiler,  # noqa: F401
    utils,
)

if TYPE_CHECKING:
    from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class Falcon(DatabaseSyncer):
    """
    Interact with a Falcon database.
    """

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "falcon"

    database: str = "cs_tools"
    schema_: str = pydantic.Field("falcon_default_schema", alias="schema")
    thoughtspot: ThoughtSpot = pydantic.Field(default_factory=utils.maybe_fetch_from_context)
    ignore_load_balancer_redirect: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.engine.create_mock_engine("sqlite://", self.sql_query_to_api_call)  # type: ignore[assignment]

    def __finalize__(self):
        try:
            _ = self.thoughtspot.session_context

        except errors.NoSessionEstablished:
            self.thoughtspot.login()

        # Create the database and schema if they doesn't exist; idempotent
        self.thoughtspot.tql.command(command=f"CREATE DATABASE {self.database};")
        self.thoughtspot.tql.command(command=f"CREATE SCHEMA {self.database}.{self.schema};")
        super().__finalize__()

    def __repr__(self):
        return f"<FalconSyncer cluster='{self.thoughtspot.config.thoughtspot.url}'>"

    def compile_query(self, query: sa.sql.expression.Executable) -> str:
        """Convert a SQL query into a string."""
        compiled = query.compile(dialect=self.engine.dialect)  # type: ignore[attr-defined]
        return compiled.string.strip() + ";"

    def sql_query_to_api_call(self, sql: sa.schema.ExecutableDDLElement, *_multiparams, **_params):
        """Convert SQL queries into ThoughtSpot remote TQL commands."""
        query = self.compile_query(sql)
        self.thoughtspot.tql.command(command=query, database=self.database)

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tablename: str) -> TableRows:
        """SELECT rows from Falcon."""
        table = self.metadata.tables[tablename]
        query = self.compile_query(table.select())
        data = self.thoughtspot.tql.query(statement=query, database=self.database)

        # Clean the incoming data
        model = next(model for model in self.models if model.__tablename__ == tablename)
        rows = [model.validated_init(**row) for row in data[0].get("data", [])]
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: TableRows) -> None:
        """INSERT rows into SQLite."""
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        data = utils.roundtrip_json_for_falcon(data)
        name = f"{self.database}_{self.schema_}_{tablename}"

        with sync_utils.temp_csv_for_upload(tmp=self.thoughtspot.config.temp_dir, filename=name, data=data) as file:
            upload_options: dict[str, Any] = {
                "ignore_node_redirect": self.ignore_load_balancer_redirect,
                "database": self.database,
                "schema_": self.schema_,
                "table": tablename,
            }

            if self.load_strategy == "APPEND":
                pass

            if self.load_strategy == "TRUNCATE":
                upload_options["empty_target"] = True

            if self.load_strategy == "UPSERT":
                raise NotImplementedError("coming soon..")

            try:
                self.thoughtspot.tsload.upload(file, **upload_options)

            except (httpx.ConnectError, httpx.ConnectTimeout):
                r = f"could not connect at [b blue]{self.thoughtspot.api.v1.dataservice_url}[/]"
                m = ""

                if self.thoughtspot.api.v1.dataservice_url.host != self.thoughtspot.config.thoughtspot.url:
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

                raise errors.TSLoadServiceUnreachable(reason=r, mitigation=m) from None
