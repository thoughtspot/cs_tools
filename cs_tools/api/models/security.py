from typing import Dict, List

from pydantic import validate_arguments
import httpx

from cs_tools.data.enums import GUID, AccessLevel, MetadataObject, PermissionType
from cs_tools.util import stringified_array


class _Security:
    """
    Private Security Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def share(
        self,
        type: str,
        id: List[str],
        permissions: Dict[str, AccessLevel],
        emailshares: List[str] = None,
        notify: bool = True,
        message: str = None
    ) -> httpx.Response:
        """
        Share objects with users/groups in specified share modes.

        NOTE:
            THIS MODEL ENDPOINT DEVIATES FROM THE REST API CONTRACT!

            In the form data, 'permission' expects a toplevel key in the
            mapping called 'permissions', which then maps to the
            guid -> access permission map.

            {"3a879a56-ae47-435f-8a23-c07362cffe7c": "MODIFY"}

            ..turns into..

            {
                "permissions": {
                    "3a879a56-ae47-435f-8a23-c07362cffe7c": {
                        "shareMode": "MODIFY"
                    }
                }
            }
        """
        r = self.rest_api.request(
                'POST',
                'security/share',
                privacy='private',
                data={
                    'type': type,
                    'id': stringified_array(id),
                    'permission': {
                        'permissions': {
                            guid: {'shareMode': access_level.value}
                            for guid, access_level in permissions.items()
                        }
                    },
                    'emailshares': emailshares or [],
                    'notify': notify,
                    'message': message
                }
            )
        return r

    @validate_arguments
    def defined_permission(self, type: str, id: List[str]) -> httpx.Response:
        """
        Get defined permissions information for a given list of objects.
        """
        r = self.rest_api.request(
                'POST',
                'security/definedpermission',
                privacy='private',
                data={'type': type, 'id': stringified_array(id)}
            )
        return r


class Security:
    """
    Public Security Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    @validate_arguments
    def metadata_permissions(
        self,
        type: MetadataObject,
        id: List[GUID],
        dependentshare: bool = False,
        permissiontype: PermissionType = PermissionType.explicit
    ) -> httpx.Response:
        """
        Query object permission details for multiple object types and IDs.
        """
        r = self.rest_api.request(
                'GET',
                'security/metadata/permissions',
                privacy='public',
                params={
                    'type': type.value,
                    'id': stringified_array(id),
                    'dependentshare': dependentshare,
                    'permissiontype': permissiontype.value
                }
            )
        return r
