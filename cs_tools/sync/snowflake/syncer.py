from __future__ import annotations  # noqa: I001

from . import _monkey  # noqa: F401

from typing import TYPE_CHECKING, Any, Literal, Optional
import functools as ft
import logging
import pathlib
import uuid

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from pydantic_core import PydanticCustomError
from snowflake.sqlalchemy import URL
import pydantic
import sqlalchemy as sa
import sqlmodel

from cs_tools import __version__
from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import DatabaseSyncer

from . import const

if TYPE_CHECKING:
    from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class Snowflake(DatabaseSyncer):
    """
    Interact with a Snowflake database.
    """

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "snowflake"

    account_name: str
    username: str
    warehouse: str
    role: str
    database: str
    authentication: Literal["basic", "key-pair", "sso", "oauth"]
    schema_: str = pydantic.Field(default="PUBLIC", alias="schema")
    secret: Optional[str] = None
    private_key_path: Optional[pydantic.FilePath] = None
    log_level: Literal["debug", "info", "warning"] = "warning"

    @pydantic.field_validator("secret", mode="before")
    def ensure_auth_secret_given(cls, value: Any, info: pydantic.ValidationInfo) -> Any:
        if info.data.get("authentication") == "sso" or value is not None:
            return value

        if info.data.get("authentication") == "basic":
            raise PydanticCustomError("missing", "Field required, you must provide a password", {"secret": value})

        if info.data.get("authentication") == "oauth":
            raise PydanticCustomError("missing", "Field required, you must provide an oauth token", {"secret": value})

    @pydantic.field_validator("private_key_path", mode="before")
    def ensure_pk_path_given(cls, value: Any, info: pydantic.ValidationInfo) -> Any:
        if info.data.get("authentication") != "key-pair" or value is not None:
            return value
        raise PydanticCustomError("missing", "Field required", {"private_key_path": value})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logging.getLogger("snowflake").setLevel(self.log_level.upper())

        self._engine = sa.create_engine(self.make_url())
        self.metadata = sqlmodel.MetaData(schema=self.schema_)

    def __repr__(self) -> str:
        account_name = self.account_name
        username = self.username
        role = self.role
        warehouse = self.warehouse
        return f"<SnowflakeSyncer ACCOUNT='{account_name}', USER='{username}', ROLE='{role}', WAREHOUSE='{warehouse}'>"

    def _fetch_private_key(self) -> bytes:
        """
        Summarized from the Snowflake SQLAlchemy documentation.

        https://github.com/snowflakedb/snowflake-sqlalchemy/tree/main#key-pair-authentication-support
        """
        assert self.private_key_path is not None
        pem_data = self.private_key_path.read_bytes()
        passphrase = self.secret.encode() if self.secret is not None else self.secret
        private_key = serialization.load_pem_private_key(data=pem_data, password=passphrase, backend=default_backend())
        pk_as_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        return pk_as_bytes

    def make_url(self) -> URL:
        """Format a connection string for the Snowflake JDBC driver."""
        url_kwargs: dict[str, Any] = {
            "account": self.account_name,
            "user": self.username,
            "database": self.database,
            "schema": self.schema_,
            "warehouse": self.warehouse,
            "role": self.role,
            "connect_args": {
                "session_parameters": {"query_tag": f"thoughtspot.cs_tools (v{__version__})"},
            },
        }

        # SNOWFLAKE DOCS:
        # https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect#connecting-using-the-default-authenticator
        if self.authentication == "basic":
            url_kwargs["authenticator"] = "snowflake"
            url_kwargs["password"] = self.secret

        # SNOWFLAKE DOCS:
        # https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect#using-key-pair-authentication-key-pair-rotation
        if self.authentication == "key-pair":
            url_kwargs["authenticator"] = "snowflake"
            url_kwargs["connect_args"]["private_key"] = self._fetch_private_key()

        # SNOWFLAKE DOCS:
        # https://docs.snowflake.com/en/user-guide/admin-security-fed-auth-use#browser-based-sso
        if self.authentication == "sso":
            url_kwargs["authenticator"] = "externalbrowser"

        # SNOWFLAKE DOCS:
        # https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect#connecting-with-oauth
        if self.authentication == "oauth":
            url_kwargs["authenticator"] = "oauth"
            url_kwargs["token"] = self.secret

        return URL(**url_kwargs)

    def stage_and_put(self, tablename: str, *, data: TableRows) -> str:
        """ """
        # ==============================================================================================================
        # DEFINE WHERE TO UPLOAD
        # ==============================================================================================================
        stage_name = f"{self.database}.{self.schema_}.TMP_STAGE_{tablename}_{uuid.uuid4().hex[:5]}"

        # fmt: off
        SQL_TEMP_STAGE = sa.sql.text(
            f"""
            CREATE TEMPORARY STAGE {stage_name}
            COMMENT = 'a temporary landing spot for CS Tools (+github: thoughtspot/cs_tools) syncer data dumps'
            FILE_FORMAT = (
                TYPE = CSV
                FIELD_DELIMITER = '|'
                NULL_IF = ( '\\N' )
                FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            )
        """
        )
        # fmt: on
        r = self.session.execute(SQL_TEMP_STAGE)
        log.debug("Snowflake response >> CREATE STAGE\n%s", r.scalar())

        # ==============================================================================================================
        # SAVE & UPLOAD CSV
        # ==============================================================================================================
        with sync_utils.make_tempfile_for_upload(directory=pathlib.Path("."), filename=tablename, data=data) as fd:
            fp = pathlib.Path(fd.name)

            # fmt: off
            SQL_PUT = sa.sql.text(
                f"""
                PUT 'file://{fp.as_posix()}' @{stage_name}
                PARALLEL = 4
                AUTO_COMPRESS = TRUE
                """
            )
            # fmt: on
            r = self.session.execute(SQL_PUT)
            log.debug("Snowflake response >> PUT FILE\n%s", r.scalar())

        return stage_name

    def copy_into(self, *, into: str, from_: str) -> None:
        # ==============================================================================================================
        # MOVE FILE FROM STAGE INTO TABLE
        # ==============================================================================================================
        # fmt: off
        SQL_COPY_INTO = sa.sql.text(
            f"""
            COPY INTO {into}
            FROM {from_}
            ON_ERROR = ABORT_STATEMENT
            PURGE = TRUE
            """
        )
        # fmt: on
        r = self.session.execute(SQL_COPY_INTO)
        log.debug("Snowflake response >> COPY INTO\n%s", r.scalar())

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tablename: str) -> TableRows:
        """SELECT rows from Snowflake."""
        table = self.metadata.tables[f"{self.schema_}.{tablename}"]
        rows = self.session.execute(table.select())
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: TableRows) -> None:
        """INSERT rows into Snowflake."""
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        table = self.metadata.tables[f"{self.schema_}.{tablename}"]
        stage = self.stage_and_put(tablename=tablename, data=data)

        if self.load_strategy == "APPEND":
            self.copy_into(from_=f"@{stage}", into=tablename)

        if self.load_strategy == "TRUNCATE":
            self.session.execute(table.delete())
            self.copy_into(from_=f"@{stage}", into=tablename)

        if self.load_strategy == "UPSERT":
            prepared = ft.partial(sync_utils.merge_into, table)
            sync_utils.batched(prepared, session=self.session, data=data, max_parameters=const.SNOWFLAKE_MAX_VARIABLES)
