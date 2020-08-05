import logging

import requests


_log = logging.getLogger(__name__)


class APIBase:
    """
    Base class for implementing the ThoughtSpot API.
    """
    def __init__(self, ts):
        self.config = ts.config
        self.http = ts.session

    @property
    def base_url(self):
        """
        Base API URl.
        """
        return f'https://{self.config.host}:{self.config.port}/callosum/v1'

    # TODO:
    #
    # def __getattr__(self, item):
    #     """
    #     API method lookup.

    #     TS-Swagger uses a mix of lowercase and camelCase. We do our best to
    #     consolidate that here.
    #     """
    #     try:
    #         endpoint = item.lower().replace('_', '')
    #     except AttributeError:
    #         raise ... from None

    # NOTE:
    #   need to create a mapping of existing methods and their lowercase
    #   representation, match on lowercase, and return the existing method.
    #   This should help lessen any confusion between the Swagger interface and
    #   the python one. (ie, a Cx using the TS SDK but copying from /swagger)
    #
    #     try:
    #         method = self.__dict__[endpoint]
    #     except KeyError:
    #         raise ... from None

    #     return method

    def _request(self, *args, **kwargs) -> requests.Response:
        """
        Make a generic request.
        """
        # TODO: implement a sane rate limit?
        return self.http.request(*args, **kwargs)

    def get(self, url: str) -> requests.Response:
        """
        Make a GET request.
        """
        return self.http._request('GET', url, )

    def post(self, url: str, *, data: dict) -> requests.Response:
        """
        Make a POST request.
        """
        return self.http._request('POST', url, data=data)

    def delete(self, url: str) -> requests.Response:
        """
        Make a DELETE request.
        """
        return self.http._request('DELETE', url)


class TSPublic(APIBase):
    """
    Public APIs
    """
    def __init__(self, ts):
        super().__init__(ts)
        self.version = '1'

    @property
    def base_url(self):
        """
        Base public APIs URl.
        """
        return f'{super().base_url}/tspublic/v{self.version}'
