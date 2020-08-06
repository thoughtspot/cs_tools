import requests

from thoughtspot.models.dependency import Dependency
from thoughtspot.models.metadata import PrivateMetadata, Metadata
from thoughtspot.models.auth import Session


class ThoughtSpot:

    def __init__(self, ts_config):
        self.config = ts_config
        self.session = requests.Session()

        # set up our session
        self.session.update({'X-Requested-By': 'ThoughtSpot'})

        if ts_config.disable_ssl:
            self.session.verify = False

        # add in all our model endpoints
        self._session = Session(self)
        self._metadata = PrivateMetadata(self)
        self._dependency = Dependency(self)
        self.metadata = Metadata(self)
