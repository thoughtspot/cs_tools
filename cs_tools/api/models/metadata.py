from typing import Any, Dict, List
import json

from pydantic import validate_arguments
import httpx

from cs_tools.api.util import stringified_array
from cs_tools.data.enums import (
    AccessLevel,
    GUID,
    MetadataObject,
    MetadataObjectSubtype,
    MetadataCategory,
    Principal,
    SortOrder,
    TMLImportPolicy,
    TMLType,
)


class _Metadata:
    """
    Private Metadata Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def edoc_type_id(
        self,
        id: GUID,
        type: str=MetadataObject.logical_table,
        formattype: str='YAML'
    ) -> httpx.Response:
        """
        Returns EDoc representation of metadata object.
        """
        r = self.rest_api.request(
                'GET',
                f'metadata/edoc/{type.value}/{id}',
                privacy='private',
                params={'formattype': formattype}
            )
        return r

    @validate_arguments
    def edoc_export_epack(self, request: Dict[str, Any]) -> httpx.Response:
        """
        Export a list of objects as edocs packaged in a zip file.

        request looks like:

        {
            "object": [
                {"id": "0291f1cd-5f8e-4d96-80e2-e5ef1aa6c44f", "type":"QUESTION_ANSWER_BOOK"},
                {"id": "4bcaadb4-031a-4afd-b159-2c0c0f194c42", "type":"PINBOARD_ANSWER_BOOK"}
            ],
            "export_dependencies": false
        }
        """
        r = self.rest_api.request(
                'POST',
                'metadata/edoc/exportEPack',
                privacy='private',
                data={'request': json.dumps(request)}
            )
        return r

    @validate_arguments
    def assigntag(
        self,
        id: List[GUID],
        type: List[MetadataObject],
        tagid: List[GUID]
    ) -> httpx.Response:
        """
        Assign tags to metadata objects; types[i] corresponds to ids[i].
        """
        r = self.rest_api.request(
                'POST',
                'metadata/assigntag',
                privacy='private',
                data={
                    # NOTE: This is an API data parsing error.. data shouldn't need to
                    # be stringified.
                    'id': stringified_array(id),
                    'type': stringified_array([_.value for _ in type]),
                    'tagid': stringified_array(tagid)
                }
            )
        return r

    @validate_arguments
    def unassigntag(
        self,
        id: List[GUID],
        type: List[MetadataObject],
        tagid: List[GUID]
    ) -> httpx.Response:
        """
        Un-assign tags to metadata objects; types[i] corresponds to ids[i].
        """
        r = self.rest_api.request(
                'POST',
                'metadata/unassigntag',
                privacy='private',
                data={
                    # NOTE: This is an API data parsing error.. data shouldn't need to
                    # be stringified.
                    'id': stringified_array(id),
                    'type': stringified_array([_.value for _ in type]),
                    'tagid': stringified_array(tagid)
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
                data={
                    'type': type.value,
                    'subtype': subtype.value if subtype is not None else None,
                    'name': name,
                    'description': description,
                    'content': content,
                    'save': save,
                    'clientstate': clientstate
                }
            )
        return r

    @validate_arguments
    def list(
        self,
        type: MetadataObject = MetadataObject.pinboard,
        subtypes: List[MetadataObjectSubtype] = None,
        ownertypes: MetadataObjectSubtype = None,
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
                    'tagname': [tagname] if tagname is not None else None,
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
                    # NOTE: This is an API data parsing error.. data shouldn't need to
                    # be stringified.
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
        subtypes: List[MetadataObjectSubtype] = None,
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

    @validate_arguments
    def details(
        self,
        id: List[GUID],
        type: MetadataObject = MetadataObject.logical_table,
        showhidden: bool = False,
        dropquestiondetails: bool = False,
        version: int = -1
    ) -> httpx.Response:
        """
        Details of one or more metadata objects in the repository.
        """
        r = self.rest_api.request(
                'GET',
                'metadata/details',
                privacy='public',
                params={
                    'type': type.value,
                    'id': id,
                    'showhidden': showhidden,
                    'dropquestiondetails': dropquestiondetails,
                    'version': version
                }
            )
        return r

    @validate_arguments
    def tml_export(
        self,
        export_ids: List[GUID],
        format_type: TMLType = TMLType.yaml,
        export_associated: bool = False,
    ) -> httpx.Response:
        """
        Details of one or more metadata objects in the repository.
        """
        r = self.rest_api.request(
                'POST',
                'metadata/tml/export',
                privacy='public',
                data={
                    'export_ids': stringified_array(export_ids),
                    'format_type': format_type.value,
                    'export_associated': export_associated
                }
            )
        return r

    @validate_arguments
    def tml_import(
            self,
            import_objects: List[str],
            import_policy: TMLImportPolicy = TMLImportPolicy.validate_only,
            force_create: bool = False,
    ) -> httpx.Response:
        """
        Details of one or more metadata objects in the repository.
        :param import_objects: List of TML objects as YAML format
        :param import_policy: The import policy to use (q.v.)
        :param force_create: If true, force creation of new objects.
        """

        r = self.rest_api.request(
            'POST',
            'metadata/tml/import',
            headers={'Accept': 'text/plain'},
            privacy='public',
            data={
                'import_objects': json.dumps(import_objects),
                'import_policy': import_policy.value,
                'force_create': str(force_create).lower()
            }
        )
        return r
