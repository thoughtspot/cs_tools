import logging

import httpx

from cs_tools.models import TSPublic


log = logging.getLogger(__name__)


#


class User(TSPublic):
    """
    Public Metadata Services.
    """

    @property
    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/user'

    def list(self) -> httpx.Response:
        """
        Fetch users and groups.
        """
        r = self.get(f'{self.base_url}/list')
        return r
