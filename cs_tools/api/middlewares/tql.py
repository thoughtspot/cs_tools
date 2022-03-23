from typing import Any, Dict, List, Tuple
import logging
import json

from pydantic.typing import Annotated
from pydantic import validate_arguments, Field

from cs_tools.data.enums import Privilege
from cs_tools.errors import InsufficientPrivileges


log = logging.getLogger(__name__)
REQUIRED_PRIVILEGES = set([
    Privilege.can_administer_thoughtspot,
    Privilege.can_manage_data
])


class TQLMiddleware:
    """
    """
    def __init__(self, ts):
        self.ts = ts

    def _check_privileges(self) -> None:
        """
        """
        if not set(self.ts.me.privileges).intersection(REQUIRED_PRIVILEGES):
            raise InsufficientPrivileges(
                user=self.ts.me,
                service='remote TQL',
                required_privileges=REQUIRED_PRIVILEGES
            )

    @validate_arguments
    def query(
        self,
        statement: str,
        *,
        sample: int = 50,
        database: str = None,
        schema_: Annotated[str, Field(alias='schema')] = 'falcon_default_schema',
        http_timeout: int = 5.0
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
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
            'context': {
                'database': database,
                'schema': schema_,
                'server_schema_version': -1
            },
            'options': {
                'query_options': {
                    'pagination': {},
                    'query_results_apply_top_row_count': sample,
                }
            },
            'query': {
                'statement': statement
            }
        }

        r = self.ts.api.ts_dataservice.query(data, timeout=http_timeout)
        d = [json.loads(_) for _ in r.iter_lines() if _]
        print(d)
        raise
        return d['result']['message']

    @validate_arguments
    def command(
        self,
        command: str,
        *,
        database: str = None,
        schema_: Annotated[str, Field(alias='schema')] = 'falcon_default_schema',
        raise_errors: bool = False,
        http_timeout: int = 5.0
    ) -> List[Dict[str, Any]]:
        """
        """
        self._check_privileges()

        data = {
            'context': {
                'database': database,
                'schema': schema_,
                'server_schema_version': -1
            },
            'query': {
                'statement': command
            }
        }

        r = self.ts.api.ts_dataservice.query(data, timeout=http_timeout)

        d = [json.loads(_) for _ in r.iter_lines() if _]
        d = r.json()
        log.debug(d)
        return d['result']['message']
