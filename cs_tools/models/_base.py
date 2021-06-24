import logging
import json

import httpx


log = logging.getLogger(__name__)


class APIBase:
    """
    Base class for implementing the ThoughtSpot API.
    """
    def __init__(self, ts):
        self.config = ts.config
        self.http = ts.http

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

        return f'{host}{port}'

    def _request(self, method, url, *args, **kwargs) -> httpx.Response:
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

        # don't log the password
        secure = kwargs.copy()
        secure.pop('password', None)
        log.debug(f'>> {method} to {url} with data:\nargs={args}\nkwargs={secure}')

        r = self.http.request(method, url, *args, **kwargs)
        log.debug(f'<< {r.status_code} from {url}')

        try:
            r.raise_for_status()
        except Exception:
            log.exception('HTTP Error')
            raise

        return r

    def get(self, url: str, *args, **kwargs) -> httpx.Response:
        """
        Make a GET request.
        """
        return self._request('GET', url, *args, **kwargs)

    def post(self, url: str, *args, **kwargs) -> httpx.Response:
        """
        Make a POST request.
        """
        return self._request('POST', url, *args, **kwargs)

    def delete(self, url: str) -> httpx.Response:
        """
        Make a DELETE request.
        """
        return self._request('DELETE', url)


class TSPublic(APIBase):
    """
    Base model for Public APIs.
    """
    def __init__(self, ts):
        super().__init__(ts)
        self.version = '1'

    @property
    def base_url(self):
        """
        Base public APIs URl.
        """
        return f'{super().base_url}/callosum/v1/tspublic/v{self.version}'


class TSPrivate(APIBase):
    """
    Base model for Private APIs.
    """

    @property
    def base_url(self):
        """
        Base private APIs URl.
        """
        return f'{super().base_url}/callosum/v1'

    def _request(self, method, url, *args, **kwargs) -> httpx.Response:
        """
        Make a generic request.
        """
        log.warning(
            f'UNSUPPORTED API CALL\n\n{method} to {url} is using a private and '
            'unsupported API!\n'
        )
        return super()._request(method, url, *args, **kwargs)
