from pydantic import validate_arguments
import httpx


class _Periscope:
    """
    Undocumented Periscope API.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    def alert_getalerts(self) -> httpx.Response:
        """
        """
        r = self.rest_api.request('GET', 'alert/getalerts', privacy='periscope')
        return r

    def sage_getsummary(self) -> httpx.Response:
        """
        """
        r = self.rest_api.request('GET', 'sage/getsummary', privacy='periscope')
        return r

    @validate_arguments
    def sage_combinedtableinfo(self, nodes: str = 'all') -> httpx.Response:
        """
        """
        r = self.rest_api.request(
                'GET',
                'sage/combinedtableinfo',
                privacy='periscope',
                params={'nodes': nodes}
            )
        return r

    def falcon_getsummary(self) -> httpx.Response:
        """
        """
        r = self.rest_api.request('GET', 'falcon/getsummary', privacy='periscope')
        return r

    def orion_getstats(self) -> httpx.Response:
        """
        """
        r = self.rest_api.request('GET', 'orion/getstats', privacy='periscope')
        return r

    def orion_listsnapshots(self) -> httpx.Response:
        """
        """
        r = self.rest_api.request('GET', 'orion/listsnapshots', privacy='periscope')
        return r
