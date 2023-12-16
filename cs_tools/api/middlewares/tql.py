from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import json
import logging

import pydantic

from cs_tools.errors import InsufficientPrivileges
from cs_tools.types import RecordsFormat

if TYPE_CHECKING:
    import pathlib

    from cs_tools._compat import Annotated
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


def _to_table(headers, rows=None):
    if rows is None:
        rows = []

    header = [column["name"] for column in headers]
    data = [dict(zip(header, row["v"])) for row in rows]
    return data


class TQLMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    def query(
        self,
        statement: str,
        *,
        sample: int = 50,
        database: Optional[str] = None,
        schema_: Annotated[str, pydantic.Field(alias="schema")] = "falcon_default_schema",
    ) -> RecordsFormat:
        """

        Parameters
        ----------
        statement: str
          query to execute in Falcon

        sample : int, default 50
          number of records to fetch from Falcon, use a negative number to express "all"
        """
        if not self.ts.session_context.user.is_data_manager:
            raise InsufficientPrivileges(
                user=self.ts.session_context.user, service="remote TQL", required_privileges="Can Manage Data"
            )

        data = {
            "context": {"database": database, "schema": schema_, "server_schema_version": -1},
            "options": {
                "query_options": {
                    "pagination": {},
                    "query_results_apply_top_row_count": sample,
                }
            },
            "query": {"statement": statement},
        }

        r = self.ts.api.v1.dataservice_query(data=data)
        i = [json.loads(_) for _ in r.iter_lines() if _]

        out = []

        for row in i:
            if "table" in row["result"]:
                out.append({"data": _to_table(**row["result"]["table"])})

            if "message" in row["result"]:
                out.append({"messages": row["result"]["message"]})

        return out

    def command(
        self,
        command: str,
        *,
        database: Optional[str] = None,
        schema_: str = "falcon_default_schema",
        # raise_errors: bool = False,
    ) -> RecordsFormat:
        """ """
        if not self.ts.session_context.user.is_data_manager:
            raise InsufficientPrivileges(
                user=self.ts.session_context.user, service="remote TQL", required_privileges="Can Manage Data"
            )

        if not command.strip().endswith(";"):
            command = f"{command.strip()};"

        data = {
            "context": {"database": database, "schema": schema_, "server_schema_version": -1},
            "query": {"statement": command},
        }

        r = self.ts.api.v1.dataservice_query(data=data)
        i = [json.loads(_) for _ in r.iter_lines() if _]

        out = []

        for row in i:
            if "table" in row["result"]:
                out.append({"data": _to_table(**row["result"]["table"])})

            if "message" in row["result"]:
                out.append({"messages": row["result"]["message"]})

        return out

    def script(self, fp: pathlib.Path) -> RecordsFormat:
        """ """
        if not self.ts.session_context.user.is_data_manager:
            raise InsufficientPrivileges(
                user=self.ts.session_context.user, service="remote TQL", required_privileges="Can Manage Data"
            )

        with fp.open() as f:
            data = {
                "context": {"schema": "falcon_default_schema", "server_schema_version": -1},
                "script_type": 1,
                "script": f.read(),
            }

        r = self.ts.api.v1.dataservice_script(data=data)
        i = [json.loads(_) for _ in r.iter_lines() if _]

        out = []

        for row in i:
            if "table" in row["result"]:
                out.append({"data": _to_table(**row["result"]["table"])})

            if "message" in row["result"]:
                out.append({"messages": row["result"]["message"]})

        return out
