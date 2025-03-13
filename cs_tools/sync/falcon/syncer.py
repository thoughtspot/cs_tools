from __future__ import annotations

from typing import Any
import json
import logging
import pathlib

import pydantic
import sqlalchemy as sa

from cs_tools import (
    _types,
    errors,
    utils as cs_tools_utils,
)
from cs_tools.api import workflows
from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import DatabaseSyncer
from cs_tools.thoughtspot import ThoughtSpot

from . import (
    compiler,  # noqa: F401
    utils,
)

_LOG = logging.getLogger(__name__)


class Falcon(DatabaseSyncer):
    """Interact with a Falcon database."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "falcon"

    database: str = "cs_tools"
    schema_: str = pydantic.Field("falcon_default_schema", alias="schema")
    thoughtspot: ThoughtSpot = pydantic.Field(default_factory=utils.check_if_keyword_needed, validate_default=False)
    ignore_load_balancer_redirect: bool = False
    wait_for_dataload_completion: bool = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.engine.create_mock_engine("sqlite://", self.sql_query_to_api_call)  # type: ignore[assignment]
        self._falcon_ctx: _types.TQLQueryContext = {
            "database": self.database,
            "schema": self.schema_,
            "server_schema_version": -1,
        }

    def __finalize__(self):
        if self.thoughtspot is None:
            return

        try:
            _ = self.thoughtspot.session_context

        except errors.NoSessionEstablished:
            self.thoughtspot.login()

        assert self.thoughtspot.session_context.user.auth_context == "BASIC", "FalconSyncer only supports BASIC AUTH."

        # Create the database and schema if they doesn't exist; idempotent
        self.sql_query_to_api_call(sql=sa.text(f"CREATE DATABASE {self.database}"))
        self.sql_query_to_api_call(sql=sa.text(f"CREATE SCHEMA {self.database}.{self.schema_}"))
        super().__finalize__()

    def __repr__(self):
        return f"<FalconSyncer cluster='{self.thoughtspot.config.thoughtspot.url}' @ {self.database}.{self.schema_}>"

    def compile_query(self, query: sa.sql.ClauseElement) -> str:
        """Convert a SQL query into a string."""
        compiled = query.compile(dialect=self.engine.dialect)
        return compiled.string.strip() + ";"

    def sql_query_to_api_call(self, sql: sa.sql.ClauseElement, *_multiparams, **_params) -> _types.APIResult:
        """Convert SQL queries into ThoughtSpot remote TQL commands."""
        query = self.compile_query(sql)

        # ISSUE A QUERY VIA THE REMOTE TQL SERVICE.
        coro = workflows.tql.query(query, falcon_context=self._falcon_ctx, http=self.thoughtspot.api)
        data = cs_tools_utils.run_sync(coro)

        _LOG.debug(f">>> QUERY\n{query}")
        _LOG.debug(f"<<< DATA\n{json.dumps(data, indent=4)}")

        # SET THE NEW FALCON CONTEXT.
        self._falcon_ctx = data["curr_falcon_context"]

        return data

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tablename: str) -> _types.TableRowsFormat:
        """SELECT rows from Falcon."""
        table = self.metadata.tables[tablename]

        raw_data = self.sql_query_to_api_call(sql=table.select())

        # SEE cs_tools.api.workflows.tql.query FOR PAYLOAD.
        assert isinstance(raw_data["data"], list), "Raw Data returned from the cs_tools TQL workflow is malformed."

        return raw_data["data"]

    def dump(self, tablename: str, *, data: _types.TableRowsFormat) -> None:
        """INSERT rows into Falcon."""
        if not data:
            _LOG.warning(f"no data to write to syncer {self}")
            return

        temp = self.thoughtspot.config.temp_dir
        name = f"{self.database}_{self.schema_}_{tablename}"
        data = utils.roundtrip_json_for_falcon(data)

        with sync_utils.temp_csv_for_upload(tmp=temp, filename=name, data=data, include_header=True) as fd:
            auth_options = {
                "username": self.thoughtspot.config.thoughtspot.username,
                "password": self.thoughtspot.config.thoughtspot.decoded_password,
            }
            upload_options: dict[str, Any] = {
                "database": self.database,
                "schema": self.schema_,
                "table": tablename,
                "has_header_row": True,
                "date_time_format": utils.FMT_TSLOAD_DATETIME,
                "ignore_node_redirect": self.ignore_load_balancer_redirect,
            }

            if self.load_strategy == "APPEND":
                upload_options["empty_target"] = False

            if self.load_strategy == "TRUNCATE":
                upload_options["empty_target"] = True

            if self.load_strategy == "UPSERT":
                raise NotImplementedError("Falcon does not offer UPSERT / MERGE support.")

            c = workflows.tsload.upload_data(fd, auth_info=auth_options, **upload_options, http=self.thoughtspot.api)
            cycle_id = cs_tools_utils.run_sync(c)

        if self.wait_for_dataload_completion:
            c = workflows.tsload.wait_for_dataload_completion(cycle_id=cycle_id, http=self.thoughtspot.api)  # type: ignore[assignment]
            _ = cs_tools_utils.run_sync(c)
