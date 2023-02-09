from __future__ import annotations

from typing import TYPE_CHECKING, List
import logging

from pydantic import validate_arguments
import httpx

from cs_tools.errors import ContentDoesNotExist
from cs_tools.types import GUID, RecordsFormat, UserProfile
from cs_tools.api import _utils

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot


class GroupMiddleware:
    """
    Functions to simplify using the group API
    """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    @validate_arguments
    def guid_for(self, group_name: str) -> GUID:
        """
        Return the GUID for a given Group.
        """
        if _utils.is_valid_guid(group_name):
            return group_name

        try:
            r = self.ts.api.group_read(group_name=group_name)
        except httpx.HTTPStatusError as e:
            if e.response.is_client_error:
                info = {
                    "reason": f"Group '{group_name}' not found.  Group names are case sensitive. You can find a "
                              f"group's 'Group Name' in the Admin panel.",
                    "mitigation": "Verify the name and try again.",
                    "type": "Group",
                }
                raise ContentDoesNotExist(**info) from None

            raise e

        return r.json()["header"]["id"]

    @validate_arguments
    def users_in(self, group_name: str, *, is_directly_assigned: bool=True) -> List[RecordsFormat]:
        """
        Return the User headers for a given Group.
        """
        if _utils.is_valid_guid(group_name):
            group_guid = group_name
        else:
            group_guid = self.guid_for(group_name)

        r = self.ts.api.group_list_users(group_guid=group_guid)
        users_profiles: List[UserProfile] = r.json()
        users = []

        if not users_profiles:
            info = {
                "reason": "Group names are case sensitive. You can find a group's 'Group Name' in the Admin panel.",
                "mitigation": "Verify the name and try again.",
                "type": "Group",
            }
            raise ContentDoesNotExist(**info) from None

        for user in users_profiles:
            if is_directly_assigned and group_guid in user["assignedGroups"]:
                users.append(user["header"])

            if not is_directly_assigned and group_guid in user["inheritedGroups"]:
                users.append(user["header"])

        return users
