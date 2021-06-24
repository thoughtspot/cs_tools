import logging.config
import datetime as dt
import logging

import httpx

from cs_tools.models.ts_dataservice import TSDataService
from cs_tools.models.dependency import _Dependency
from cs_tools.models.periscope import _Periscope
from cs_tools.models.metadata import Metadata, _Metadata
from cs_tools.models.security import _Security
from cs_tools.models.session import _Session
from cs_tools.models.auth import Session
from cs_tools.models.user import User
from cs_tools.schema.user import User as UserSchema
from cs_tools.errors import CertificateVerifyFailure
from cs_tools.const import APP_DIR


log = logging.getLogger(__name__)


class ThoughtSpot:
    """
    """
    def __init__(self, ts_config):
        self.config = ts_config
        self._setup_logging()

        # set up our session
        # NOTE: base_url is a valid parameter for httpx.Client
        self.http = httpx.Client(timeout=180.0, verify=not ts_config.thoughtspot.disable_ssl)
        self.http.headers.update({'X-Requested-By': 'ThoughtSpot'})

        # set in __enter__()
        self.logged_in_user = None
        self.thoughtspot_version = None

        # add remote TQL & tsload services
        self.ts_dataservice = TSDataService(self)

        # add public API endpoints
        self.metadata = Metadata(self)
        self.auth = Session(self)
        self.user = User(self)

        # add private API endpoints
        self._dependency = _Dependency(self)
        self._metadata = _Metadata(self)
        self._periscope = _Periscope(self)
        self._security = _Security(self)
        self._session = _Session(self)

    def _clean_logs(self, now):
        logs_dir = APP_DIR / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)

        # keep only the last 25 logfiles
        lifo = sorted(logs_dir.iterdir(), reverse=True)

        for idx, log in enumerate(lifo):
            if idx > 25:
                log.unlink()

    def _setup_logging(self):
        logging.getLogger('urllib3').setLevel(logging.ERROR)

        now = dt.datetime.now().strftime('%Y-%m-%dT%H_%M_%S')
        self._clean_logs(now)

        logging.basicConfig(
            filename=f'{APP_DIR}/logs/{now}.log',
            format='[%(levelname)s - %(asctime)s] '
                   '[%(name)s - %(module)s.%(funcName)s %(lineno)d] '
                   '%(message)s',
            level=self.config.logging.level
        )

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

        self.logged_in_user = UserSchema(
            guid=rj['userGUID'], name=rj['userName'], display_name=rj['userDisplayName'],
            email=rj['userEmail'], privileges=rj.get('privileges', ['AUTHORING'])
        )

        self.thoughtspot_version = rj['releaseVersion']
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.auth.logout()
