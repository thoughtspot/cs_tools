from typing import List

from pydantic import validate_arguments
import httpx

from cs_tools.data.enums import GUID, ResultsFormat
from cs_tools.api.util import stringified_array


class Logs:
    """
    Public Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def topics(
        self,
        topic: str = 'security_logs',
        fromEpoch: int = None,  # in milliseconds
        toEpoch: int = None,    # in milliseconds
    ) -> httpx.Response:
        """
        Get the pinboard data from thoughtspot system.
        """
        r = self.rest_api.request(
                'GET',
                f'logs/topics/{topic}',
                privacy='public',
                params={'fromEpoch': fromEpoch, 'toEpoch': toEpoch}
            )
        return r
