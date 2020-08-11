import logging.config
import logging

import requests

from thoughtspot.models.dependency import Dependency
from thoughtspot.models.metadata import PrivateMetadata, Metadata
from thoughtspot.models.auth import Session


_log = logging.getLogger(__name__)


class ThoughtSpot:

    def __init__(self, ts_config):
        self.config = ts_config
        self.session = requests.Session()

        # set up logging
        logging.getLogger('urllib3').setLevel(logging.ERROR)

        try:
            logging.config.dictConfig(ts_config.logging)
            _log.info('set up provided logger at level DEBUG')
        except ValueError:
            logging.basicConfig(
                format='[%(levelname)s - %(asctime)s] '
                       '[%(name)s - %(module)s.%(funcName)s %(lineno)d] '
                       '%(message)s',
                level=logging.DEBUG
            )

            level = logging.getLevelName(logging.getLogger('root').getEffectiveLevel())
            _log.info(f'set up the default logger at level {level}')

        # set up our session
        self.session.headers.update({'X-Requested-By': 'ThoughtSpot'})

        if ts_config.thoughtspot.disable_ssl:
            self.session.verify = False
            requests.packages.urllib3.disable_warnings()

        # add in all our model endpoints
        self._session = Session(self)
        self._metadata = PrivateMetadata(self)
        self._dependency = Dependency(self)
        self.metadata = Metadata(self)

    def __enter__(self):
        self._session.login()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._session.logout()
