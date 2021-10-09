from pydantic import validate_arguments
import httpx


class _Session:
    """
    Private User Session Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def group_list_user(self, groupid: str) -> httpx.Response:
        """
        Get list of users belonging to a group.
        """
        r = self.rest_api.request(
                'GET',
                f'session/group/listuser/{groupid}',
                privacy='private',
            )
        return r

    @validate_arguments
    def group_list_group(self, groupid: str) -> httpx.Response:
        """
        Get list of groups belonging to a group.
        """
        r = self.rest_api.request(
                'GET',
                f'session/group/listgroup/{groupid}',
                privacy='private',
            )
        return r

    @validate_arguments
    def info(self) -> httpx.Response:
        """
        Get session information.
        """
        r = self.rest_api.request(
                'GET',
                'session/info',
                privacy='private',
            )
        return r
