from typing import Any, Dict, List, Union
import json

from pydantic import validate_arguments
import httpx

from cs_tools.api.util import stringified_array
from cs_tools.data.enums import (
    GUID,
    SortOrder,
)


class _Connection:
    """
    Private Connection Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def detail(
        self,
        id: GUID,
        sort: str = SortOrder.default.value,
        sortascending: bool = None,
        pattern: str = None,
        tagname: List[str] = None,
        showhidden: bool = False
    ) -> httpx.Response:

        r = self.rest_api.request(
                'GET',
                f'connection/detail/{id}',
                privacy='private',
                params={
                    "sort": sort,
                    "sortascending": sortascending,
                    "pattern": pattern,
                    "tagname": tagname,
                    "showhidden": showhidden
                }
            )
        return r

