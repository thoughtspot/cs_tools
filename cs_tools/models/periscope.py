import logging

import httpx

from cs_tools.settings import APIParameters
from cs_tools.models import TSPrivate


log = logging.getLogger(__name__)


class SageCombinedTableInfoParameters(APIParameters):
    nodes: str = 'all'


class _Periscope(TSPrivate):
    """
    Periscope Services.
    """

    @property
    def base_url(self):
        """
        """
        host = self.config.thoughtspot.host
        port = self.config.thoughtspot.port

        if port:
            port = f':{port}'
        else:
            port = ''

        return f'{host}{port}/periscope'

    def alert_getalerts(self) -> httpx.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/alerts/getalerts')
        return r

    def alert_getevents(self) -> httpx.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/alerts/getevents')
        return r

    def sage_getsummary(self) -> httpx.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/sage/getsummary')
        return r

    def sage_combinedtableinfo(self, **parameters) -> httpx.Response:
        """
        TODO
        """
        p = SageCombinedTableInfoParameters(**parameters)
        r = self.get(f'{self.base_url}/sage/combinedtableinfo', params=p.json())
        return r

    def falcon_getsummary(self) -> httpx.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/falcon/getsummary')
        return r

    def orion_getstats(self) -> httpx.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/orion/getstats')
        return r

    def orion_listsnapshots(self) -> httpx.Response:
        """
        TODO
        """
        r = self.get(f'{self.base_url}/orion/listsnapshots')
        return r
