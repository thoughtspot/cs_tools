from typing import Any, Dict, List

from pydantic import validate_arguments
import httpx

from cs_tools.util import stringified_array
from cs_tools._enums import (
    GUID,
    MetadataObject,
    LogicalTableSubtype,
    MetadataCategory,
    SortOrder,
    AccessLevel,
    Principal
)


class _Metadata:
    """
    Private Metadata Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def assigntag(
        self,
        id: List[GUID],
        type: MetadataObject,
        tagid: List[GUID]
    ) -> httpx.Response:
        """
        Assign tags to metadata objects; types[i] corresponds to ids[i].
        """
        r = self.rest_api.request(
                'POST',
                'metadata/assigntag',
                privacy='private',
                params={
                    'id': id,
                    'type': type.value,
                    'tagid': tagid
                }
            )
        return r

    @validate_arguments
    def unassigntag(
        self,
        id: List[GUID],
        type: MetadataObject,
        tagid: List[GUID]
    ) -> httpx.Response:
        """
        Un-assign tags to metadata objects; types[i] corresponds to ids[i].
        """
        r = self.rest_api.request(
                'POST',
                'metadata/unassigntag',
                privacy='private',
                params={
                    'id': id,
                    'type': type.value,
                    'tagid': tagid
                }
            )
        return r

    @validate_arguments
    def create(
        self,
        name: str,
        type: MetadataObject = MetadataObject.saved_answer,
        subtype: MetadataObject = None,
        description: str = None,
        content: Dict[str, Any] = None,
        save: bool = True,
        clientstate: Any = None
    ) -> httpx.Response:
        """
        Create a new metadata object in the repository.
        """
        r = self.rest_api.request(
                'POST',
                'metadata/create',
                privacy='private',
                params={
                    'type': type.value,
                    'subtype': subtype.value,
                    'name': name,
                    'description': description,
                    'content': content,
                    'save': save,
                    'clientstate': clientstate
                }
            )
        return r

    @validate_arguments
    def save(
        self,
        type: MetadataObject,
        content: Dict[str, Any],
        forcesave: bool = False,
    ) -> httpx.Response:
        """
        Save metadata object in the repository.
        """
        r = self.rest_api.request(
                'POST',
                'metadata/save',
                privacy='private',
                params={
                    'type': type.value,
                    'content': content,
                    'forcesave': forcesave,
                }
            )
        return r

    @validate_arguments
    def list(
        self,
        type: MetadataObject = MetadataObject.pinboard,
        subtypes: List[LogicalTableSubtype] = None,
        ownertypes: LogicalTableSubtype = None,
        category: MetadataCategory = MetadataCategory.all,
        sort: SortOrder = SortOrder.default,
        sortascending: bool = None,
        offset: int = -1,
        batchsize: int = None,
        tagname: List[str] = None,
        pattern: str = None,
        showhidden: bool = False,
        skipids: List[GUID] = None,
        fetchids: List[GUID] = None,
        auto_created: bool = None,
    ) -> httpx.Response:
        """
        List of metadata objects in the repository.
        """
        r = self.rest_api.request(
                'GET',
                'metadata/list',
                privacy='private',
                params={
                    'type': type.value,
                    'subtypes': stringified_array([_.value for _ in subtypes or ()]),
                    'ownertypes': stringified_array([_.value for _ in ownertypes or ()]),
                    'category': category.value,
                    'sort': sort.value,
                    'sortascending': sortascending,
                    'offset': offset,
                    'batchsize': batchsize,
                    'tagname': stringified_array([_ for _ in tagname or ()]),
                    'pattern': pattern,
                    'skipids': stringified_array([_ for _ in skipids or ()]),
                    'fetchids': stringified_array([_ for _ in fetchids or ()]),
                    'auto_created': auto_created
                }
            )
        return r

    @validate_arguments
    def listas(
        self,
        offset: int = -1,
        batchsize: int = None,
        pattern: str = None,
        principalid: GUID = None,
        minimumaccesslevel: AccessLevel = AccessLevel.no_access,
        type: Principal = Principal.group,
    ) -> httpx.Response:
        """
        List of metadata objects in the repository as seen by a User/Group.
        """
        r = self.rest_api.request(
                'GET',
                'metadata/listas',
                privacy='private',
                params={
                    'offset': offset,
                    'batchsize': batchsize,
                    'pattern': pattern,
                    'principalid': principalid,
                    'minimumaccesslevel': minimumaccesslevel.value,
                    'type': type.value,
                }
            )
        return r

    @validate_arguments
    def detail(
        self,
        id: GUID,
        type: MetadataObject = None,
        showhidden: bool = False,
        dropquestiondetails: bool = False,
        inboundrequesttype: int = 10000,
        doUpdate: bool = True
    ) -> httpx.Response:
        """
        Detail of a metadata object in the repository.
        """
        r = self.rest_api.request(
                'GET',
                f'metadata/detail/{id}',
                privacy='private',
                params={
                    'id': id,
                    'type': type.value,
                    'showhidden': showhidden,
                    'dropquestiondetails': dropquestiondetails,
                    'inboundrequesttype': inboundrequesttype,
                    'doUpdate': doUpdate
                }
            )
        return r

    @validate_arguments
    def delete(
        self,
        id: List[GUID],
        type: MetadataObject = None,
        includedisabled: bool = False,
    ) -> httpx.Response:
        """
        Delete metadata object(s) from the repository.
        """
        r = self.rest_api.request(
                'POST',
                'metadata/delete',
                privacy='private',
                data={
                    'type': None if type is None else type.value,
                    'id': stringified_array([_ for _ in id or ()]),
                    'includedisabled': includedisabled
                }
            )
        return r

    @validate_arguments
    def list_columns(
        self,
        id: GUID,
        showhidden: bool = False,
    ) -> httpx.Response:
        """
        Get list of all logical columns of a given logical table.
        """
        r = self.rest_api.request(
                'GET',
                f'metadata/listcolumns/{id}',
                privacy='private',
                params={'id': id, 'showhidden': showhidden}
            )
        return r


class Metadata:
    """
    Public Metadata Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def list_viz_headers(self, id: GUID) -> httpx.Response:
        """
        Get the visualization headers from the ThoughtSpot system.
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
        skipids: List[GUID] = None,
        fetchids: List[GUID] = None,
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
                    'tagname': stringified_array([_ for _ in tagname or ()]),
                    'pattern': pattern,
                    'skipids': stringified_array([_ for _ in skipids or ()]),
                    'fetchids': stringified_array([_ for _ in fetchids or ()]),
                    'auto_created': auto_created
                }
            )
        return r
