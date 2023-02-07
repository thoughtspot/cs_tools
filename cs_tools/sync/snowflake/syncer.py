from typing import List, Dict, Any
import logging
import enum

from snowflake.sqlalchemy import snowdialect, URL
from pydantic.dataclasses import dataclass
from pydantic import root_validator
import sqlalchemy as sa

from cs_tools.utils import chunks
from cs_tools import __version__

from .const import MAX_EXPRESSIONS_MAGIC_NUMBER

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
        # - they forcibly log EVERYTHING...
        # - implement COMMIT: 93ee7cc, PR#275 prior to pypi release
        snowdialect.SnowflakeDialect.supports_statement_cache = False
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

        for chunk in chunks(data, n=MAX_EXPRESSIONS_MAGIC_NUMBER):
            with self.cnxn.begin():
                self.cnxn.execute(t.insert(), chunk)
