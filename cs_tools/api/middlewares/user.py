from __future__ import annotations

from typing import Optional, Any, TYPE_CHECKING
import logging

from pydantic import validate_arguments

from cs_tools.data.enums import GUID
from cs_tools.errors import AmbiguousContentError, ContentDoesNotExist
from cs_tools.api import _utils

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot


log = logging.getLogger(__name__)


class UserMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    @validate_arguments
    def all(self) -> list[dict[str, Any]]:
        """
        Get all users in ThoughtSpot.
        """
        offset = 0
        users = []

        while True:
            # user/list doesn't offer batching..
            r = self.ts.api.metadata_list(metadata_type="USER", batchsize=50, offset=offset)
            data = r.json()
            users.extend(data["headers"])
            offset += len(data["headers"])

            if data["isLastBatch"]:
                break

        return users

    @validate_arguments
    def get(self, principal: str | GUID, *, error_if_ambiguous: bool = True) -> dict[str, Any]:
        """
        Find a user in ThoughtSpot.

        Parameters
        ----------
        principal : str or GUID
          GUID or username or display name of the user

        error_if_ambiguous : bool, default True
          whether or not to raise an error if multiple users are identified

        Raises
        ------
        ContentDoesNotExist
          raised when the user by 'principal' does not exist

        AmbiguousContentError
          raise when multiple users match the identifier 'principal'
        """
        if _utils.is_valid_guid(principal):
            kw = {"fetch_guids": [principal]}
        else:
            kw = {"pattern": principal}

        r = self.ts.api.metadata_list(metadata_type="USER", **kw)
        user = r.json()["headers"]

        if not user:
            raise ContentDoesNotExist(type="USER", reason=f"No user found with the name [blue]{principal}")

        if error_if_ambiguous:
            if len(user) > 1:
                raise AmbiguousContentError(type="user", name=principal)

            user = user[0]

        return user

    @validate_arguments
    def get_guid(self, name: str) -> Optional[GUID]:
        """
        Returns the GUID for a user or None if the user wasn't found.

        Parameters
        ----------
        name : str
          the user's username, e.g. somebody@somecompany.com
        """
        r = self.ts.api.user_read(name=name)
        return r.json()["header"]["id"]
