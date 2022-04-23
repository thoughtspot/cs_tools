from typing import Any, Dict, List
import logging
import enum

from pydantic.dataclasses import dataclass
from snowflake.sqlalchemy import URL, snowdialect
from pydantic import Field
import sqlalchemy as sa

from cs_tools import __version__
from cs_tools.util import chunks

from .const import MAX_EXPRESSIONS_MAGIC_NUMBER


log = logging.getLogger(__name__)


class AuthType(enum.Enum):
    local = 'local'
    multi_factor = 'multi-factor'


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
    schema_: str = Field('PUBLIC', alias='schema')
    auth_type: AuthType = AuthType.local
    truncate_on_load: bool = True

    # DATABASE ATTRIBUTES
    __is_database__ = True
    metadata = None

    def __post_init_post_parse__(self):
        # silence the noise that snowflake dialect creates
        # - they forcibly log EVERYTHING...
        # - implement COMMIT: 93ee7cc, PR#275 prior to pypi release
        snowdialect.SnowflakeDialect.supports_statement_cache = False
        logging.getLogger('snowflake').setLevel('WARNING')

        url = URL(
            account=self.snowflake_account_identifier,
            user=self.username,
            password=self.password,
            database=self.database,
            schema=self.schema_,
            warehouse=self.warehouse,
            role=self.role
        )
    
        connect_args = {
            'session_parameters': {
                'query_tag': f'thoughtspot.cs_tools (v{__version__})'
            }
        }

        if self.auth_type != AuthType.local:
            connect_args['authenticator'] = 'externalbrowser'

        self.engine = sa.create_engine(url, connect_args=connect_args)
        self.cnxn = self.engine.connect()

        # decorators must be declared here, SQLAlchemy doesn't care about instances
        sa.event.listen(sa.schema.MetaData, 'after_create', self.capture_metadata)

    def capture_metadata(self, metadata, cnxn, **kw):
        self.metadata = metadata

    def __repr__(self):
        return f"<Database ({self.name}) sync: conn_string='{self.engine.url}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return 'snowflake'

    def load(self, table: str) -> List[Dict[str, Any]]:
        t = self.metadata.tables[table]

        with self.cnxn.begin():
            r = self.cnxn.execute(t.select())

        return [dict(_) for _ in r]

    def dump(self, table: str, *, data: List[Dict[str, Any]]) -> None:
        t = self.metadata.tables[table]

        if self.truncate_on_load:
            with self.cnxn.begin():
                self.cnxn.execute(t.delete())

        for chunk in chunks(data, n=MAX_EXPRESSIONS_MAGIC_NUMBER):
            with self.cnxn.begin():
                self.cnxn.execute(t.insert(), chunk)
