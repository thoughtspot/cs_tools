import logging

from thoughtspot.settings import APIParameters
import requests

from thoughtspot_internal.models import TSPrivate


_log = logging.getLogger(__name__)


class SageCombinedTableInfoParameters(APIParameters):
    nodes: str = 'all'


class Periscope(TSPrivate):
    """
    Metadata Services.
    """

    @property
    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/periscope'

    def alert_getalerts(self) -> requests.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/alerts/getalerts')
        return r

    def alert_getevents(self) -> requests.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/alerts/getevents')
        return r

    def sage_getsummary(self) -> requests.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/sage/getsummary')
        return r

    def sage_combinedtableinfo(self, **parameters) -> requests.Response:
        """
        TODO
        """
        p = SageCombinedTableInfoParameters(**parameters)
        r = self.get(f'{self.base_url}/sage/sage_combinedtableinfo', params=p.json())
        return r

    def falcon_getsummary(self) -> requests.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/falcon/getsummary')
        return r

    def orion_getstats(self) -> requests.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/orion/getstats')
        return r

    def orion_listsnapshots(self) -> requests.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/orion/listsnapshots')
        return r
