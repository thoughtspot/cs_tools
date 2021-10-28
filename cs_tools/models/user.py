from typing import List

from pydantic import validate_arguments
import httpx

from cs_tools.util import stringified_array
from cs_tools._enums import GUID


class User:
    """
    Public User Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    def list(self) -> httpx.Response:
        """
        Fetch users and groups.
        """
        r = self.rest_api.request('GET', 'user/list', privacy='public')
        return r

    @validate_arguments
    def transfer_ownership(
        self,
        fromUserName: str,
        toUserName: str,
        objectsID: List[GUID]
    ) -> httpx.Response:
        """
        Transfer ownership of all objects from one user to another.
        """
        r = self.rest_api.request(
                'POST',
                'user/transfer/ownership',
                privacy='public',
                params={
                    'fromUserName': fromUserName,
                    'toUserName': toUserName,
                    # technically not available until ts7.sep.cl-109 or greater, but
                    # query parameters don't usually cause 4xx or 5xx errors
                    'objectsID': stringified_array(objectsID or ())
                }
            )
        return r
