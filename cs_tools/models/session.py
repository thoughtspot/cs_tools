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

    @validate_arguments
    def login(
        self,
        username: str,
        password: str,
        rememberme: bool = True,
        disableSAMLAutoRedirect: bool = False
    ) -> httpx.Response:
        """
        Log in to ThoughtSpot.

        This implementation slightly deviates from the REST API contract. There
        is a URL flag to disable the automatic redirect for SAML authentication
        that really only makes sense to be part of the session/login call. We
        implement this as a private parameter in this method's signature.
        """
        r = self.rest_api.request(
                'POST',
                'session/login',
                privacy='private',
                data={
                    'username': username,
                    'password': password,
                    'rememberme': rememberme
                },
                params={'disableSAMLAutoRedirect': disableSAMLAutoRedirect}
            )
        return r

    def logout(self) -> httpx.Response:
        """
        Log out of ThoughtSpot.
        """
        r = self.rest_api.request('POST', 'session/logout', privacy='private')
        return r
