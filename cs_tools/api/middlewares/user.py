from __future__ import annotations

from typing import TYPE_CHECKING
import logging

from pydantic import validate_arguments
import httpx

from cs_tools.errors import ContentDoesNotExist
from cs_tools.types import RecordsFormat, GUID
from cs_tools.api import _utils

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot


log = logging.getLogger(__name__)


class UserMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    @validate_arguments
    def all(self) -> RecordsFormat:
        """
        Get all users in ThoughtSpot.
        """
        users = []

        while True:
            # user/list doesn't offer batching..
            r = self.ts.api.metadata_list(metadata_type="USER", batchsize=50, offset=len(users))
            data = r.json()
            users.extend(data["headers"])

            if data["isLastBatch"]:
                break

        return users

    @validate_arguments
    def guid_for(self, username: str) -> GUID:
        """
        Return the GUID for a given User.
        """
        if _utils.is_valid_guid(username):
            return username

        try:
            r = self.ts.api.user_read(name=username)
        except httpx.HTTPStatusError as e:
            if e.response.is_client_error:
                info = {
                    "reason": "User names are case sensitive. You can find a User's 'username' in the Admin panel.",
                    "mitigation": "Verify the name and try again.",
                }
                raise ContentDoesNotExist(**info) from None

            raise e

        return r.json()["header"]["id"]
