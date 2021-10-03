import logging
import copy

import httpx

from cs_tools.helpers.secrets import reveal
from cs_tools.modelsv2 import (
    Metadata,
    TSDataService
)


log = logging.getLogger(__name__)


class _RESTAPIv1:
    """
    Implementation of the REST API v1.

    Model endpoints are classified by how they appear in Swagger.
    """
    def __init__(self, config, ts):
        self._config = config
        self._ts = ts
        self._http = httpx.Client(
            headers={'X-Requested-By': 'ThoughtSpot'},
            verify=not config.thoughtspot.disable_ssl,
            timeout=180.0,
            base_url=config.thoughtspot.fullpath
        )

        # remote TQL & tsload services
        self.ts_dataservice = TSDataService(self)

        # public API endpoints
        self.metadata = Metadata(self)
        # self.user = User(self)

        # private API endpoints
        # self._dependency = _Dependency(self)
        # self._metadata = _Metadata(self)
        # self._periscope = _Periscope(self)
        # self._security = _Security(self)
        # self._session = _Session(self)

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        privacy: str='public',
        **kw
    ) -> httpx.Response:
        """
        Make a request over to the API.

        Parameters
        ----------
        method : str
            http method to call: one of GET, POST, PUT, DELETE

        endpoint : str
            api endpoint to call, as the slug appears in swagger

            examples..
              metadata/list
              session/login

            If an absolute URL is given, ignore the base URL set on the rest
            client interface. In this setting, the privacy keyword argument is
            ignored.

        privacy : str = 'public'
            privacy setting for the api call, which determines the route

            examples..
                     public = callosum/v1/tspublic/v1
                    private = callusom/v1
                dataservice = ts_dataservice/v1/public

        **kw
            passed into the httpx.request call
        """
        if httpx.URL(endpoint).is_relative_url:
            _privacy = {
                # IF NOT FOUND IN THIS MAPPING, THEN IT'S AN UNDOCUMENTED API
                'public': 'callosum/v1/tspublic/v1',
                'private': 'callosum/v1',
                'dataservice': 'ts_dataservice/v1/public'
            }

            endpoint = f'{_privacy.get(privacy, privacy)}/{endpoint}'

            if privacy not in _privacy:
                log.warning(f'using an undocumented api! :: {endpoint}')

        # pop the password so it doesn't get logged
        try:
            secure = copy.deepcopy(kw)
        except TypeError:
            secure = copy.deepcopy({k: v for k, v in kw.items() if k not in ('file', 'files')})

        secure.get('data', {}).pop('password', None)
        log.debug(f'>> {endpoint} with data:\n\tkwargs={secure}')

        meth = getattr(self._http, method.lower())
        r = meth(endpoint, **kw)
        r.raise_for_status()  # pass thru errors
        log.debug(f'<< HTTP: {r.status_code}')

        if r.text:
            log.debug('<< CONTENT:\n\n%s', r.text)

        return r

    # AUTH

    def login(self) -> httpx.Response:
        """
        Log in to ThoughtSpot.
        """
        data = {
            'username': self._config.auth['frontend'].username,
            'password': reveal(self._config.auth['frontend'].password).decode(),
            'rememberme': True
        }
        r = self.request('POST', 'session/login', privacy='private', data=data)
        return r

    def logout(self) -> httpx.Response:
        """
        Log out of ThoughtSpot.
        """
        return self.request('POST', 'session/logout', privacy='private')
