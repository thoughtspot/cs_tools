import logging

import httpx

from cs_tools.helpers.secrets import reveal
from cs_tools.models._base import APIBase
from cs_tools.errors import AuthenticationError


log = logging.getLogger(__name__)


class Session(APIBase):
    """
    User Session Services.
    """

    @property
    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/callosum/v1/session'

    def login(self):
        """
        Authenticate and login a user.
        """
        data = {
            'username': self.config.auth['frontend'].username,
            'password': reveal(self.config.auth['frontend'].password).decode(),
            'rememberme': True
        }

        url = f'{self.base_url}/login'

        if self.config.thoughtspot.disable_sso:
            url = f'{url}?disableSAMLAutoRedirect=true'

        r = self.post(url, data=data)

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            log.error(f'login to ThoughtSpot was unsuccessful: {status}')
            raise AuthenticationError(username=data['username'])
        else:
            log.debug('login to ThoughtSpot was successful')

        return r

    def logout(self):
        """
        Logout current user.
        """
        r = self.post(f'{self.base_url}/logout')

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            log.error(f'logout of ThoughtSpot was unsuccessful: {status}')
        else:
            log.debug('logout of ThoughtSpot was successful')
