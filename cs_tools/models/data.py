from typing import List

from pydantic import validate_arguments
import httpx

from cs_tools._enums import GUID, ResultsFormat
from cs_tools.util import stringified_array


class Data:
    """
    Public Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def pinboarddata(
        self,
        id: GUID,
        vizid: List[GUID] = None,
        batchsize: int = -1,
        pagenumber: int = -1,
        offset: int = -1,
        formattype: ResultsFormat = ResultsFormat.values
    ) -> httpx.Response:
        """
        Get the pinboard data from thoughtspot system.
        """
        r = self.rest_api.request(
                'POST',
                'pinboarddata',
                privacy='public',
                params={
                    'id': id,
                    'vizid': stringified_array([_ for _ in vizid or ()]),
                    'batchsize': batchsize,
                    'pagenumber': pagenumber,
                    'offset': offset,
                    'formattype': formattype.value,
                }
            )
        return r

    @validate_arguments
    def searchdata(
        self,
        query_string: str,
        data_source_guid: GUID,
        batchsize: int = -1,
        pagenumber: int = -1,
        offset: int = -1,
        formattype: ResultsFormat = ResultsFormat.values
    ) -> httpx.Response:
        """
        Search data from a specific data source in thoughtspot system.
        """
        r = self.rest_api.request(
                'POST',
                'searchdata',
                privacy='public',
                params={
                    'query_string': query_string,
                    'data_source_guid': data_source_guid,
                    'batchsize': batchsize,
                    'pagenumber': pagenumber,
                    'offset': offset,
                    'formattype': formattype.value,
                }
            )
        return r
