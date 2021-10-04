from typing import List

from pydantic import validate_arguments
import httpx

from cs_tools.util import stringified_array
from cs_tools._enums import (
    MetadataObject,
    LogicalTableSubtype,
    MetadataCategory,
    SortOrder
)


class Metadata:
    """
    Public Metadata Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def list_viz_headers(self, id: str) -> httpx.Response:
        """
        Get the visualization headers from the ThoughtSpot system.

        Parameters
        ----------
        guid : str
            GUID of the pinboard
        """
        r = self.rest_api.request(
                'GET',
                'metadata/listvizheaders',
                privacy='public',
                params={'id': id}
            )
        return r

    @validate_arguments
    def list_object_headers(
        self,
        type: MetadataObject = MetadataObject.pinboard,
        subtypes: List[LogicalTableSubtype] = None,
        category: MetadataCategory = MetadataCategory.all,
        sort: SortOrder = SortOrder.default,
        sortascending: bool = None,
        offset: int = -1,
        batchsize: int = None,
        tagname: List[str] = None,
        pattern: str = None,
        skipids: List[str] = None,
        fetchids: List[str] = None,
        auto_created: bool = None
    ) -> httpx.Response:
        """
        List of metadata object headers in the repository.
        """
        r = self.rest_api.request(
                'GET',
                'metadata/listobjectheaders',
                privacy='public',
                params={
                    'type': type.value,
                    'subtypes': stringified_array([_.value for _ in subtypes or ()]),
                    'category': category.value,
                    'sort': sort.value,
                    'sortascending': sortascending,
                    'offset': offset,
                    'batchsize': batchsize,
                    'tagname': tagname,
                    'pattern': pattern,
                    'skipids': skipids,
                    'fetchids': fetchids,
                    'auto_created': auto_created
                }
            )
        return r
