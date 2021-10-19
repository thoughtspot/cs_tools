from typing import List, Optional

from pydantic import validate_arguments
import httpx

from cs_tools._enums import MetadataObject
from cs_tools.util import stringified_array


class _Dependency:
    """
    Private dependency Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def list_dependents(
        self,
        id: List[str],
        type: MetadataObject = MetadataObject.logical_column,
        batchsize: int = -1,
        offset: int = -1,
        timeout: Optional[int] = -1
    ) -> httpx.Response:
        """
        Metadata objects referencing given object.

        This implementation slightly deviates from the REST API contract.
        Offset is not advertised to be part of the contract, but is an allowed
        value whenever batchsize is included.
        """
        timeout = self.rest_api._http.timeout if timeout == -1 else timeout

        r = self.rest_api.request(
                'POST',
                'dependency/listdependents',
                privacy='private',
                data={
                    'type': type.value,
                    # NOTE: This is an API data parsing error.. data shouldn't need to
                    # be stringified.
                    'id': stringified_array(id),
                    'batchsize': batchsize,
                    'offset': offset
                },
                timeout=timeout
            )
        return r
