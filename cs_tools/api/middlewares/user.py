from __future__ import annotations

from typing import TYPE_CHECKING
import logging

import httpx

from cs_tools.api import _utils
from cs_tools.errors import ContentDoesNotExist

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot
    from cs_tools.types import GUID, RecordsFormat


log = logging.getLogger(__name__)


class UserMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    def all(self, batchsize: int = 50) -> RecordsFormat:  # noqa: A003
        """
        Get all users in ThoughtSpot.
        """
        users = []

        while True:
            # user/list doesn't offer batching..
            r = self.ts.api.v1.metadata_list(metadata_type="USER", batchsize=batchsize, offset=len(users))
            data = r.json()
            users.extend(data["headers"])

            if data["isLastBatch"]:
                break

        return users

    def guid_for(self, username: str) -> GUID:
        """
        Return the GUID for a given User.
        """
        if _utils.is_valid_guid(username):
            return username

        try:
            r = self.ts.api.v1.user_read(username=username)
        except httpx.HTTPStatusError as e:
            if e.response.is_client_error:
                info = {
                    "reason": "User names are case sensitive. You can find a User's 'username' in the Admin panel.",
                    "mitigation": "Verify the name and try again.",
                    "type": "User",
                }
                raise ContentDoesNotExist(**info) from None

            raise e

        return r.json()["header"]["id"]
