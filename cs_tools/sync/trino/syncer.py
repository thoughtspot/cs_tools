from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Optional
import logging
import pathlib

from pydantic_core import PydanticCustomError
from trino.sqlalchemy import URL
import pydantic
import sqlalchemy as sa
import sqlmodel

from cs_tools import __version__
from cs_tools.sync import utils as sync_utils
from cs_tools.sync.base import DatabaseSyncer

from . import compiler  # noqa: F401

from cs_tools import _types

log = logging.getLogger(__name__)


class Trino(DatabaseSyncer):
    """Interact with a Trino database."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "trino"

    host: pydantic.IPvAnyAddress
    port: Optional[int] = 8080
    catalog: str
    schema_: Optional[str] = pydantic.Field(default="public", alias="schema")
    authentication: Literal["basic", "jwt"]
    username: Optional[str] = None
    secret: Optional[str] = None

    @pydantic.field_validator("username", mode="before")
    def ensure_basic_auth_username_given(cls, value: Any, info: pydantic.ValidationInfo) -> Any:
        if info.data.get("authentication") == "basic" and value is None:
            raise PydanticCustomError("missing", "Field required", {"username": value})
        return value

    @pydantic.field_validator("secret", mode="before")
    def ensure_jwt_auth_secret_given(cls, value: Any, info: pydantic.ValidationInfo) -> Any:
        if info.data.get("authentication") == "jwt" and value is None:
            raise PydanticCustomError("missing", "Field required, you must provide a json web token", {"secret": value})
        return value

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.create_engine(self.make_url(), future=True)
        self.metadata = sqlmodel.MetaData(schema=self.schema_)

    def make_url(self) -> URL:
        """Format a connection string for the Trino JDBC driver."""
        url_kwargs: dict[str, Any] = {
            "host": str(self.host),
            "port": self.port,
            "catalog": self.catalog,
            "schema": self.schema_,
            "client_tags": [f"thoughtspot.cs_tools (v{__version__})"],
        }

        # TRINO DOCS:
        # https://github.com/trinodb/trino-python-client/tree/master#basic-authentication
        if self.authentication == "basic":
            url_kwargs["user"] = self.username
            url_kwargs["password"] = self.secret

        # TRINO DOCS:
        # https://github.com/trinodb/trino-python-client/tree/master#jwt-authentication
        # https://trino.io/docs/current/security/jwt.html
        if self.authentication == "jwt":
            url_kwargs["access_token"] = self.secret

        return URL(**url_kwargs)

    def __repr__(self):
        return f"<TrinoSyncer to {self.host}/{self.catalog}>"

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tablename: str) -> _types.TableRowsFormat:
        """SELECT rows from Trino."""
        table = self.metadata.tables[f"{self.schema_}.{tablename}"]
        rows = self.session.execute(table.select())
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: _types.TableRowsFormat) -> None:
        """INSERT rows into Trino."""
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        table = self.metadata.tables[f"{self.schema_}.{tablename}"]

        if self.load_strategy == "APPEND":
            sync_utils.batched(table.insert().values, session=self.session, data=data)

        if self.load_strategy == "TRUNCATE":
            self.session.execute(table.delete())
            sync_utils.batched(table.insert().values, session=self.session, data=data)

        if self.load_strategy == "UPSERT":
            sync_utils.generic_upsert(table, session=self.session, data=data)

        self.session.commit()
