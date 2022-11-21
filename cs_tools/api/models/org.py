from typing import Any, Dict, List, Union

from pydantic import validate_arguments
import httpx

from cs_tools.data.enums import (
    GUID,
)


class Org:
    """
    Public calls to the /org API
    """

    def __init__(self, rest_api):
        self.rest_api = rest_api

    def get(self, org_id=None, name=None) -> httpx.Response:
        """
        Returns the details for the org from the id or name.  Either the ID or the name must be specified.
        :param org_id: The ID for the org.
        :param name: The name for the org.
        :return: The response object.
        """
        r = self.rest_api.request(
            'GET',
            f'org',
            privacy='public',
            params={
                "id": org_id,
                "name": name,
                "orgScope": "all"  # needed by the API to work.
            }
        )
        return r


class _Org:
    """
    Private calls to the /org API
    """

    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def all(self,
            batchSize: int = -1,
            offset: int = -1,
            sort: str = "DEFAULT", #  options are DEFAULT, NAME
            sortascending: bool = True,
            pattern: str = None,
            authorguid: GUID = None,
            showinactive: bool = False
        ) -> httpx.Response:
        """
        Returns the list of all orgs that match the parameters.  Can be batched.
        :param batchSize: Size of the batch if getting batches.  -1 indicates no batching.
        :param offset: Offset.  If using batching, must track and use the offset to get the next batch.
        :param sort: Defines how to sort the results.  DEFAULT uses the ID.
        :param sortascending: If true sorts ascending, else descending.
        :param authorguid: The creator of the group.
        :param showinactive: If true, also shows inactive orgs.
        :return: The response from the call.
        """

        r = self.rest_api.request(
            'GET',
            f'org/all',
            privacy='private',
            params={
              "batchSize": batchSize,
              "offset": offset,
              "sort": sort,
              "sortascending": sortascending,
              "pattern": pattern,
              "authorguid": authorguid,
              "showinactive": showinactive,
              "orgId": "-1"  # needed by the API to work.
            }
        )
        return r
