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
            f'{method} to {url} is utilizing and unsupported API!'
        )
        return super()._request(method, url, *args, **kwargs)
