from __future__ import annotations

from typing import TYPE_CHECKING
import logging

from pydantic import validate_arguments
import httpx

from cs_tools.errors import ContentDoesNotExist
from cs_tools.types import GUID
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
            r = self.ts.api.group_read(name=group_name)
        except httpx.HTTPStatusError as e:
            if e.response.is_client_error:
                info = {
                    "reason": "Group names are case sensitive. You can find a group's 'Group Name' in the Admin panel.",
                    "mitigation": "Verify the name and try again.",
                }
                raise ContentDoesNotExist(**info) from None

            raise e

        return r.json()["header"]["id"]
