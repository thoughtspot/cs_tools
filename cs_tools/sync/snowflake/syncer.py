from typing import List, Dict, Any
import datetime as dt
import tempfile
import logging
import pathlib
import enum
import uuid

from pydantic.dataclasses import dataclass
from snowflake.sqlalchemy import URL
from pydantic import root_validator
import pyarrow.parquet as pq
import sqlalchemy as sa
import pyarrow as pa

from cs_tools import __version__

from . import utils

log = logging.getLogger(__name__)


class AuthType(enum.Enum):
    local = "local"
    multi_factor = "multi-factor"


@dataclass
class Snowflake:
    """
    Interact with a Snowflake database.
    """

    snowflake_account_identifier: str
    username: str
    password: str
    warehouse: str
    role: str
    database: str
    schema_: str = "PUBLIC"  # Field(default='PUBLIC', alias='schema')
    auth_type: AuthType = AuthType.local
    truncate_on_load: bool = True

    # DATABASE ATTRIBUTES
    __is_database__ = True

    @root_validator(pre=True)
    def prepare_aliases(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        # for some reason, Field(..., alias='...') doesn't work with dataclass but also
        # if we don't use pydantic, we don't get easy post-init setup. Whatever.
        if "schema" in values:
            values["schema_"] = values.pop("schema")
        return values

    def __post_init_post_parse__(self):
        # silence the noise that snowflake dialect creates
        logging.getLogger("snowflake").setLevel("WARNING")

        url = URL(
            account=self.snowflake_account_identifier,
            user=self.username,
            password=self.password,
            database=self.database,
            schema=self.schema_,
            warehouse=self.warehouse,
            role=self.role,
        )

        connect_args = {"session_parameters": {"query_tag": f"thoughtspot.cs_tools (v{__version__})"}}

        if self.auth_type != AuthType.local:
            connect_args["authenticator"] = "externalbrowser"

        self.engine = sa.create_engine(url, connect_args=connect_args)
        self.cnxn = self.engine.connect()
        self.metadata = sa.MetaData(schema=self.schema_)

    def __repr__(self):
        u = self.username
        w = self.warehouse
        r = self.role
        return f"<Database ({self.name}) sync: user='{u}', warehouse='{w}', role='{r}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return "snowflake"

    def load(self, table: str) -> List[Dict[str, Any]]:
        t = self.metadata.tables[f"{self.schema_}.{table}"]

        with self.cnxn.begin():
            r = self.cnxn.execute(t.select())

        return [dict(_) for _ in r]

    def dump(self, table: str, *, data: List[Dict[str, Any]]) -> None:
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        t = self.metadata.tables[f"{self.schema_}.{table}"]

        if self.truncate_on_load:
            with self.cnxn.begin():
                self.cnxn.execute(t.delete())

        # ==============================================================================================================
        # DEFINE WHERE TO UPLOAD
        # ==============================================================================================================
        stage_name = f"{self.database}.{self.schema_}.TMP_STAGE_{uuid.uuid4().hex}"

        SQL_TEMP_STAGE = (
            f"""
                CREATE TEMPORARY STAGE "{stage_name}"
                COMMENT = 'a temporary landing spot for CS Tools (+github: thoughtspot/cs_tools) syncer data dumps'
                FILE_FORMAT = (
                    TYPE = PARQUET
                    COMPRESSION = AUTO
                    NULL_IF = ( '\\N', 'None', 'none', 'null' )
                )
            """
        )
        r = self.cnxn.execute(SQL_TEMP_STAGE, _is_internal=True)
        log.debug("Snowflake response\n%s", dict(r.first()))

        # ==============================================================================================================
        # SAVE & UPLOAD PARQUET
        # ==============================================================================================================
        COMPRESSION = "gzip"
        fp = pathlib.Path(tempfile.gettempdir()) / f"output-{dt.datetime.now():%Y%m%dT%H%M%S}.parquet"
        pq.write_table(pa.Table.from_pylist(data), fp, compression=COMPRESSION)

        SQL_PUT = (
            f"""
                PUT 'file://{fp.as_posix()}' @"{stage_name}"
                PARALLEL = 4
                AUTO_COMPRESS = FALSE
                SOURCE_COMPRESSION = {COMPRESSION.upper()}
            """
        )
        r = self.cnxn.execute(SQL_PUT, _is_internal=True)
        log.debug("Snowflake response\n%s", dict(r.first()))

        # ==============================================================================================================
        # CONVERT PARQUET to TABLE
        # ==============================================================================================================
        table_name = f"{self.database}.{self.schema_}.{table.upper()}"

        SQL_COPY_INTO = (
            f"""
                COPY INTO {table_name} ({','.join([c.key for c in t.columns])})
                FROM (SELECT {','.join(map(utils.parse_field, t.columns))} FROM @"{stage_name}")
                ON_ERROR = ABORT_STATEMENT
                PURGE = TRUE
            """
        )
        r = self.cnxn.execute(SQL_COPY_INTO, _is_internal=True)
        log.debug("Snowflake response\n%s", dict(r.first()))
