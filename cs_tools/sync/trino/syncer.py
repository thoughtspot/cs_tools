from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Optional
import logging
import pathlib

from trino.sqlalchemy import URL
import pydantic
import sqlalchemy as sa

from cs_tools import __version__
from cs_tools.sync.base import DatabaseSyncer

if TYPE_CHECKING:
    from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


class Trino(DatabaseSyncer):
    """Interact with a Trino database."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "trino"

    host: int
    port: int = 8080
    catalog: str
    schema_: Optional[str] = pydantic.Field(default="public", alias="schema")
    authentication: Literal["basic", "jwt"]
    username: Optional[str] = None
    secret: Optional[str] = None

    @pydantic.model_validator(mode="before")
    @classmethod
    def ensure_secrets_given(cls, values: Any) -> Any:
        """Secrets must be provided when using any authentication except for SSO."""
        if values["authentication"] == "basic" and values["username"] is None:
            must_provide = "a user to 'username'"

            if values["password"] is None:
                must_provide += ", and optionally a password to 'secret'"

        if values["authentication"] == "jwt":
            must_provide = "a json web token to 'secret'"

        raise ValueError(f"when using {values['authentication']} authentication, you must provide {must_provide}")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._engine = sa.create_engine(self.make_url(), future=True)

    def make_url(self) -> URL:
        """Format a connection string for the Trino JDBC driver."""
        url_kwargs: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "catalog": self.catalog,
            "schema": self.schema_,
            "client_tags": [f"thoughtspot.cs_tools (v{__version__})"],
        }

        # TRINO DOCS:
        # https://github.com/trinodb/trino-python-client/tree/master#basic-authentication
        if self.authentication == "basic":
            url_kwargs["username"] = self.username
            url_kwargs["password"] = self.secret

        # TRINO DOCS:
        # https://github.com/trinodb/trino-python-client/tree/master#jwt-authentication
        # https://trino.io/docs/current/security/jwt.html
        if self.authentication == "jwt":
            url_kwargs["access_token"] = self.secret

        return URL(**url_kwargs)

    def __repr__(self):
        return f"<TrinoSyncer conn_string='{self.engine.url}'>"

    # MANDATORY PROTOCOL MEMBERS

    def load(self, tablename: str) -> TableRows:
        """SELECT rows from Trino."""
        table = self.metadata.tables[tablename]
        rows = self.session.execute(table.select())
        return [row.model_dump() for row in rows]

    def dump(self, tablename: str, *, data: TableRows) -> None:
        """INSERT rows into Trino."""
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        table = self.metadata.tables[tablename]

        if self.load_strategy == "APPEND":
            self.batched_insert(table.insert(), data=data)

        if self.load_strategy == "TRUNCATE":
            self.session.execute(table.delete())
            self.batched_insert(table.insert(), data=data)

        if self.load_strategy == "UPSERT":
            raise NotImplementedError("coming soon..")

        self.session.commit()


class Starburst(Trino):
    """Interact with a Starburst database."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "starburst"

    def __repr__(self):
        return f"<StarburstSyncer conn_string='{self.engine.url}'>"
