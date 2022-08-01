import logging

from pydantic import validate_arguments
import httpx

log = logging.getLogger(__name__)


class Group:
    """
    Public Group Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def get_group(
        self,
        id: str = None,
        name: str = None
    ) -> httpx.Response:

        params = {}
        if id:
            params['groupid'] = id
        if name:
            params['name'] = name

        r = self.rest_api.request(
                'GET',
                'group',
                privacy='public',
                params=params
            )
        return r


