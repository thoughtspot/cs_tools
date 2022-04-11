from typing import Any, Dict, List, Union
import logging

from pydantic import validate_arguments

from cs_tools._enums import GUID


log = logging.getLogger(__name__)


class ConnectionMiddleware:
    """
    Defines helper functions for dealing with /connection API calls.
    """

    def __init__(self, ts):
        self.ts = ts

    @validate_arguments
    def get_tables_for_connection(
            self,
            id: GUID,
            pattern: str = None,
            tagname: List[str] = None,
            showhidden: bool = False
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

        r = self.ts.api._connection.detail(id=id, pattern=pattern, tagname=tagname, showhidden=showhidden)
        json_tables = r.json()['tables']
        for _ in json_tables:
            h = _['header']
            tables.append({
                "id": h['id'],
                "description": h['description'],
                "name": h['name'],
                "subtype": h['type'],
                "isHidden": h['isHidden']
            })

        return tables
