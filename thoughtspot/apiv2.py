import requests

from thoughtspot.models.metadata import PrivateMetadata, Metadata
from thoughtspot.models.auth import Security


class ThoughtSpot:

    def __init__(self, ts_config):
        self.config = ts_config
        self.session = requests.Session()

        # set up our session
        self.session.update({'X-Requested-By': 'ThoughtSpot'})

        if ts_config.disable_ssl:
            self.session.verify = False

        # add in all our model endpoints
        self._security = Security(self)
        self._metadata = PrivateMetadata(self)
        self.metadata = Metadata(self)
