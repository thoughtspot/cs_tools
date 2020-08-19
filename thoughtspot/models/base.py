import logging
import json

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
        host = self.config.thoughtspot.host
        port = self.config.thoughtspot.port

        if port:
            port = f':{port}'
        else:
            port = ''

        return f'https://{host}{port}/callosum/v1'

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

    def _request(self, method, url, *args, **kwargs) -> requests.Response:
        """
        Make a generic request.
        """
        # sigh .... we are converting pydantic to json, but data and params
        # kwargs expect dictionaries... so we resort to this hack. I'm sure I
        # can find something more elegant later.
        # - NC
        if isinstance(kwargs.get('params'), str):
            kwargs['params'] = json.loads(kwargs['params'])
        if isinstance(kwargs.get('data'), str):
            kwargs['data'] = json.loads(kwargs['data'])
        # sigh/

        # TODO: implement a sane rate limit?
        _log.debug(f'>> {method} to {url}')
        r = self.http.request(method, url, *args, **kwargs)
        _log.debug(f'<< {r.status_code} from {url}')
        return r

    def get(self, url: str, *args, **kwargs) -> requests.Response:
        """
        Make a GET request.
        """
        return self._request('GET', url, *args, **kwargs)

    def post(self, url: str, *args, **kwargs) -> requests.Response:
        """
        Make a POST request.
        """
        return self._request('POST', url, *args, **kwargs)

    def delete(self, url: str) -> requests.Response:
        """
        Make a DELETE request.
        """
        return self._request('DELETE', url)


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
