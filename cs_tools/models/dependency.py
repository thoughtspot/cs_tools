from typing import List

from pydantic import validate_arguments
import httpx

from cs_tools._enums import MetadataObject


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
        batchsize: int = -1
    ) -> httpx.Response:
        """
        Metadata objects referencing given object.
        """
        r = self.rest_api.request(
                'POST',
                'dependency/listdependents',
                privacy='private',
                data={'type': type, 'id': id, 'batchsize': batchsize}
            )
        return r
