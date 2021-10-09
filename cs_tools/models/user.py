from pydantic import validate_arguments
import httpx


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
    def transfer_ownership(self, fromUserName: str, toUserName: str) -> httpx.Response:
        """
        Transfer ownership of all objects from one user to another.
        """
        r = self.rest_api.request(
                'POST',
                'user/transfer/ownership',
                privacy='public',
                params={'fromUserName': fromUserName, 'toUserName': toUserName}
            )
        return r
