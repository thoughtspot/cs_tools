from pydantic import validate_arguments
import httpx

from cs_tools.api.requirement import requires


class Logs:
    """
    Public Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    # @requires(software='7.1.1', cloud='ts7.aug.cl')
    @validate_arguments
    def topics(
        self,
        topic: str = 'security_logs',
        fromEpoch: int = None,  # in milliseconds
        toEpoch: int = None,    # in milliseconds
    ) -> httpx.Response:
        """
        Get the pinboard data from thoughtspot system.

        A single API call only supports logs streaming for maximum of 24 hrs
        duration. This is a limit on the number of concurrent S3 connections
        supported by the aws-java-sdk. We are maxed at 50 AWS S3 objects in a
        single API operation - for 24hrs data pull, that's close to 48 objects.
        """
        r = self.rest_api.request(
                'GET',
                f'logs/topics/{topic}',
                privacy='public',
                params={'fromEpoch': fromEpoch, 'toEpoch': toEpoch}
            )
        return r
