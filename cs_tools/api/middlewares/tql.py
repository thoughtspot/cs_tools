from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import json
import logging

from pydantic import Field

from cs_tools.errors import InsufficientPrivileges
from cs_tools.types import GroupPrivilege, RecordsFormat

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

    def _check_privileges(self) -> None:
        """
        Determine if the user has necessary Data Manager privileges.
        """
        REQUIRED = {GroupPrivilege.can_administer_thoughtspot, GroupPrivilege.can_manage_data}

        if not set(self.ts.me.privileges).intersection(REQUIRED):
            raise InsufficientPrivileges(user=self.ts.me, service="remote TQL", required_privileges=", ".join(REQUIRED))

    def query(
        self,
        statement: str,
        *,
        sample: int = 50,
        database: Optional[str] = None,
        schema_: Annotated[str, Field(alias="schema")] = "falcon_default_schema",
        http_timeout: int = 60.0,
    ) -> RecordsFormat:
        """

        Parameters
        ----------
        statement: str
          query to execute in Falcon

        sample : int, default 50
          number of records to fetch from Falcon, use a negative number to express "all"
        """
        self._check_privileges()

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

        r = self.ts.api.v1.dataservice_query(data=data, timeout=http_timeout)
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
        http_timeout: int = 60.0,
    ) -> RecordsFormat:
        """ """
        self._check_privileges()

        if not command.strip().endswith(";"):
            command = f"{command.strip()};"

        data = {
            "context": {"database": database, "schema": schema_, "server_schema_version": -1},
            "query": {"statement": command},
        }

        r = self.ts.api.v1.dataservice_query(data=data, timeout=http_timeout)
        i = [json.loads(_) for _ in r.iter_lines() if _]

        out = []

        for row in i:
            if "table" in row["result"]:
                out.append({"data": _to_table(**row["result"]["table"])})

            if "message" in row["result"]:
                out.append({"messages": row["result"]["message"]})

        return out

    def script(
        self,
        fp: pathlib.Path,
        *,
        # raise_errors: bool = False,
        http_timeout: int = 60.0,
    ) -> RecordsFormat:
        """ """
        self._check_privileges()

        with fp.open() as f:
            data = {
                "context": {"schema": "falcon_default_schema", "server_schema_version": -1},
                "script_type": 1,
                "script": f.read(),
            }

        r = self.ts.api.v1.dataservice_script(data=data, timeout=http_timeout)
        i = [json.loads(_) for _ in r.iter_lines() if _]

        out = []

        for row in i:
            if "table" in row["result"]:
                out.append({"data": _to_table(**row["result"]["table"])})

            if "message" in row["result"]:
                out.append({"messages": row["result"]["message"]})

        return out
