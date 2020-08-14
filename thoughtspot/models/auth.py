import logging

import requests

from thoughtspot.models.base import APIBase


_log = logging.getLogger(__name__)


class Session(APIBase):
    """
    User Session Services.
    """

    @property
    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/session'

    def login(self):
        """
        Authenticate and login a user.
        """
        data = {
            'username': self.config.auth['frontend'].username,
            'password': self.config.auth['frontend'].password,
            'rememberme': True
        }

        url = f'{self.base_url}/login'

        if self.config.thoughtspot.disable_sso:
            url = f'{url}?disableSAMLAutoRedirect=true'

        r = self.post(url, data=data)

        try:
            r.raise_for_status()
        except requests.errors.HTTPError as exc:
            _log.error(
                f'login to ThoughtSpot was unsuccessful: {exc.response.status_code}'
            )
        else:
            _log.info('login to ThoughtSpot was successful')

        return r

    def logout(self):
        """
        Logout current user.
        """
        r = self.post(f'{self.base_url}/logout')

        try:
            r.raise_for_status()
        except requests.errors.HTTPError as exc:
            _log.error(
                f'logout of ThoughtSpot was unsuccessful: {exc.response.status_code}'
            )
        else:
            _log.info('logout of ThoughtSpot was successful')
