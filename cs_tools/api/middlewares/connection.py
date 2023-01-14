from __future__ import annotations
from typing import Any
from typing import TYPE_CHECKING
import logging

from pydantic import validate_arguments

from cs_tools.data.enums import GUID

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


class ConnectionMiddleware:
    """
    Defines helper functions for dealing with /connection API calls.
    """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    @validate_arguments
    def get_tables_for_connection(
        self, id: GUID, pattern: str = None, tagname: List[str] = None, showhidden: bool = False
    ):
        """
        Returns a dictionary of where table details for the given connection.

        The return format looks like:
        [
            {
                "id": "<GUID>",
                "description":"this is a table",
                "name": "My Table",
                "subtype": "ONE_TO_ONE",
                "isHidden": "false"
            },
            {
                "id": "<GUID>",
                "description":"this is another table",
                "name": "Other Table",
                "subtype": "ONE_TO_ONE",
                "isHidden": "false"
            },
        ]
        """
        tables = []

        # replace with connection/export tables
        r = self.ts.api._connection.detail(id=id, pattern=pattern, tagname=tagname, showhidden=showhidden)

        for table in r.json()["tables"]:
            header = table["header"]

            tables.append(
                {
                    "id": header["id"],
                    "description": header["description"],
                    "name": header["name"],
                    "subtype": header["type"],
                    "isHidden": header["isHidden"],
                }
            )

        return tables
