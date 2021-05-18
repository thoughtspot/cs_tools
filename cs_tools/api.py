import logging.config
import logging

import httpx

from .models.ts_dataservice import TSDataService
from .models.dependency import _Dependency
from .models.periscope import _Periscope
from .models.metadata import Metadata, _Metadata
from .models.security import _Security
from .models.auth import Session
from .models.user import User


log = logging.getLogger(__name__)


class ThoughtSpot:
    """
    """
    def __init__(self, ts_config):
        self.config = ts_config
        self._setup_logging()

        # set up our session
        self.http = httpx.Client(timeout=10.0, verify=not ts_config.thoughtspot.disable_ssl)
        self.http.headers.update({'X-Requested-By': 'ThoughtSpot'})
        self._logged_in_user_guid = None  # set in __enter__()

        # add TQL service
        self.ts_dataservice = TSDataService(self)

        # add public API endpoints
        self.auth = Session(self)
        self.metadata = Metadata(self)
        self.user = User(self)

        # add private API endpoints
        self._dependency = _Dependency(self)
        self._metadata = _Metadata(self)
        self._periscope = _Periscope(self)
        self._security = _Security(self)

    def _setup_logging(self):
        logging.getLogger('urllib3').setLevel(logging.ERROR)

        logging.basicConfig(
            format='[%(levelname)s - %(asctime)s] '
                   '[%(name)s - %(module)s.%(funcName)s %(lineno)d] '
                   '%(message)s',
            level='INFO'
        )

        # try:
        #     logging.config.dictConfig(**self.config.logging.dict())
        #     log.info(f'set up provided logger at level {self.config.logging}')
        # except (ValueError, AttributeError):
        #     logging.basicConfig(
        #         format='[%(levelname)s - %(asctime)s] '
        #                '[%(name)s - %(module)s.%(funcName)s %(lineno)d] '
        #                '%(message)s',
        #         level=getattr(logging, self.config.logging.level)
        #     )

        #     level = logging.getLevelName(logging.getLogger('root').getEffectiveLevel())
        # log.info(f'set up the default logger at level {level}')

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
                log.error('SSL verify failed, did you mean to use flag --disable_ssl?')
                raise SystemExit(1)

        rj = r.json()
        self._logged_in_user_guid = rj['userGUID']
        self._thoughtspot_version = rj['releaseVersion']
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.auth.logout()
