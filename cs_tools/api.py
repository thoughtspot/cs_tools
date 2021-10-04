import logging.config
import logging

import httpx

from cs_tools.models.dependency import _Dependency
from cs_tools.models.periscope import _Periscope
from cs_tools.models.security import _Security
from cs_tools.models.session import _Session
from cs_tools.models.auth import Session
from cs_tools.errors import CertificateVerifyFailure


log = logging.getLogger(__name__)


class ThoughtSpot:
    """
    """
    def __init__(self, ts_config):
        self.config = ts_config

        # set up our session
        # NOTE: base_url is a valid parameter for httpx.Client
        self.http = httpx.Client(timeout=180.0, verify=not ts_config.thoughtspot.disable_ssl)
        self.http.headers.update({'X-Requested-By': 'ThoughtSpot'})

        # add public API endpoints
        self.auth = Session(self)

        # add private API endpoints
        self._dependency = _Dependency(self)
        self._periscope = _Periscope(self)
        self._security = _Security(self)
        self._session = _Session(self)

    @property
    def host(self):
        """
        URL of ThoughtSpot.
        """
        return self.config.thoughtspot.host

    def __enter__(self):
        try:
            r = self.auth.login()
        except httpx.ConnectError as e:
            if 'CERTIFICATE_VERIFY_FAILED' in str(e):
                raise CertificateVerifyFailure()

            log.exception('something went wrong.. :(')
            raise SystemExit(1)

        rj = r.json()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.auth.logout()
