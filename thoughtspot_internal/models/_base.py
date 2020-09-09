import logging

import requests

from thoughtspot.models._base import APIBase


_log = logging.getLogger(__name__)


class TSPrivate(APIBase):
    """
    Private APIs
    """

    def _request(self, method, url, *args, **kwargs) -> requests.Response:
        """
        Make a generic request.
        """
        _log.warning(
            f'UNSUPPORTED API CALL\n\n{method} to {url} is utilizing a private and unsupported API!\n'
        )
        return super()._request(method, url, *args, **kwargs)
