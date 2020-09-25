import logging.config
import logging

from thoughtspot.api import ThoughtSpot as ThoughtSpot_

from thoughtspot_internal.models.dependency import Dependency
from thoughtspot_internal.models.periscope import Periscope
from thoughtspot_internal.models.metadata import Metadata


_log = logging.getLogger(__name__)


class ThoughtSpot(ThoughtSpot_):

    def __init__(self, ts_config):
        super().__init__(ts_config)

        # add to our model endpoints
        self._metadata = Metadata(self)
        self._dependency = Dependency(self)
        self._periscope = Periscope(self)
