import logging

import httpx

from cs_tools.settings import APIParameters
from cs_tools.models import TSPublic


log = logging.getLogger(__name__)


class TransferOwnershipParameters(APIParameters):
    fromUserName: str
    toUserName: str


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

    def transfer_ownership(self, from_, to_) -> httpx.Response:
        """
        Transfer ownership of all objects from one user to another.
        """
        p = TransferOwnershipParameters(fromUserName=from_, toUserName=to_)
        r = self.post(f'{self.base_url}/transfer/ownership', params=p.json())
        return r
