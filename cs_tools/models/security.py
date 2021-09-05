from typing import List, Dict
import pydantic
import httpx
import enum

from cs_tools.util.swagger import to_array
from cs_tools.settings import APIParameters
from cs_tools.models import TSPrivate


import logging
log = logging.getLogger(__name__)


class ObjectType(enum.Enum):
    LOGICAL_COLUMN = "LOGICAL_COLUMN"              # table-, worksheet-, view-columns
    LOGICAL_TABLE = "LOGICAL_TABLE"                # tables, worksheets, views
    QUESTION_ANSWER_BOOK = "QUESTION_ANSWER_BOOK"  # answer
    PINBOARD_ANSWER_BOOK = "PINBOARD_ANSWER_BOOK"  # pinboard


class SharePermission(enum.Enum):
    MODIFY = "MODIFY"
    NO_ACCESS = "NO_ACCESS"
    READ_ONLY = "READ_ONLY"

    def __str__(self):
        return self.value


class ShareParameters(APIParameters):
    # NOTE: FORMAT OF .permission
    #
    # {
    #     'permissions': {
    #         guid: {
    #             'shareMode': permission
    #         }
    #     }
    # }
    #
    type: ObjectType = None
    id: str = None
    permission: Dict[str, Dict[str, Dict[str, SharePermission]]]
    # permission: str = ""
    emailshares: List[pydantic.EmailStr] = []
    notify: bool = True
    message: str = ""

    @pydantic.validator('id', pre=True)
    def stringify_the_array(cls, v) -> str:
        return to_array(v)

    @pydantic.validator('permission', pre=True)
    def inject_share_mode(cls, v):
        if 'permissions' in v:
            v = v['permissions']

        new_v = {}

        for group_guid, permission in v.items():
            if 'shareMode' not in permission:
                permission = {'shareMode': permission}

            new_v[group_guid] = permission

        return {'permissions': new_v}


class DefinedPermissionParameters(APIParameters):
    type: str
    id: str

    @pydantic.validator('id', pre=True)
    def stringify_the_array(cls, v) -> str:
        return to_array(v)


class _Security(TSPrivate):
    """
    Security services.
    """

    @property
    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/security'

    def share(self, **parameters) -> httpx.Response:
        """
        List of metadata objects in the repository.
        """
        p = ShareParameters(**parameters)
        # print(p.json())
        r = self.post(f'{self.base_url}/share', data=p.json())
        return r

    def defined_permission(self, **parameters) -> httpx.Response:
        """
        Get defined permissions information for a given list of objects
        """
        p = DefinedPermissionParameters(**parameters)
        r = self.post(f'{self.base_url}/definedpermission', data=p.json())
        return r
