from typing import Any, Dict, List
import logging

from pydantic.dataclasses import dataclass
import click

from .data_service import run_tql_command


log = logging.getLogger(__name__)


@dataclass
class Falcon:
    """
    Interact with Falcon.
    """
    database: str = 'cs_tools'
    schema: str = 'falcon_default_schema'

    def __post_init_post_parse__(self):
        ctx = click.get_current_context()
        self.ts = ctx.obj.thoughtspot

        self.create_database(self.database)
        self.create_table()

    def create_database(self, database: str, *, raise_on_error: bool = False):
        """
        """
        run_tql_command(self.ts, command=f'CREATE DATABASE {database};')

    def create_table(self, *, tablename: str):
        """
        """
        ...

    def __repr__(self):
        return f"<Database ({self.name}) sync>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return 'falcon'

    def load(self, directive: str) -> List[Dict[str, Any]]:
        ...

    def dump(self, directive: str, *, data: List[Dict[str, Any]]) -> None:
        ...
