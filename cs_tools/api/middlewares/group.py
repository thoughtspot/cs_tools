from __future__ import annotations

from typing import TYPE_CHECKING
import logging

from pydantic import validate_arguments
import httpx

from cs_tools.api import _utils
from cs_tools.errors import ContentDoesNotExist

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot
    from cs_tools.types import GUID, RecordsFormat, UserProfile


class GroupMiddleware:
    """
    Functions to simplify using the group API
    """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    def all(self, batchsize: int = 50) -> RecordsFormat:  # noqa: A003
        """
        Get all groups in ThoughtSpot.
        """
        groups = []

        while True:
            # user/list doesn't offer batching..
            r = self.ts.api.v1.metadata_list(metadata_type="USER_GROUP", batchsize=batchsize, offset=len(groups))
            data = r.json()
            groups.extend(data["headers"])

            if data["isLastBatch"]:
                break

        return groups

    def guid_for(self, group_name: str) -> GUID:
        """
        Return the GUID for a given Group.
        """
        if _utils.is_valid_guid(group_name):
            return group_name

        try:
            r = self.ts.api.v1.group_read(group_name=group_name)
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

    def users_in(self, group_name: str, *, is_directly_assigned: bool = True) -> list[RecordsFormat]:
        """
        Return the User headers for a given Group.
        """
        if _utils.is_valid_guid(group_name):
            group_guid = group_name
        else:
            group_guid = self.guid_for(group_name)

        r = self.ts.api.v1.group_list_users(group_guid=group_guid)
        users_profiles: list[UserProfile] = r.json()
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
