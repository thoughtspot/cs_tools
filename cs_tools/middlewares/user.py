from typing import Any, Dict, List, Union
import logging

from pydantic import validate_arguments

from cs_tools._enums import GUID
from cs_tools.errors import AmbiguousContentError, ContentDoesNotExist
from cs_tools import util


log = logging.getLogger(__name__)


class UserMiddleware:
    """
    """
    def __init__(self, ts):
        self.ts = ts

    @validate_arguments
    def all(self) -> List[Dict[str, Any]]:
        """
        Get all users in ThoughtSpot.

        Parameters
        ----------
        None

        Returns
        -------
        users : List[Dict[str, Any]]
          all user headers
        """
        offset = 0
        users = []

        while True:
            # user/list doesn't offer batching..
            r = self.ts.api._metadata.list(type='USER', batchsize=50, offset=offset)
            data = r.json()
            users.extend(data['headers'])
            offset += len(data['headers'])

            if data['isLastBatch']:
                break

        return users

    @validate_arguments
    def get(
        self,
        principal: Union[str, GUID],
        *,
        error_if_ambiguous: bool = True
    ) -> Dict[str, Any]:
        """
        Find a user in ThoughtSpot.

        Parameters
        ----------
        principal : str or GUID
          GUID or username or display name of the user

        error_if_ambiguous : bool, default True
          whether or not to raise an error if multiple users are identified

        Returns
        -------
        user : Dict[str, Any]
          user header

        Raises
        ------
        ContentDoesNotExist
          raised when the user by 'principal' does not exist

        AmbiguousContentError
          raise when multiple users match the identifier 'principal'
        """
        if util.is_valid_guid(principal):
            kw = {'fetchids': [principal]}
        else:
            kw = {'pattern': principal}

        r = self.ts.api._metadata.list(type='USER', **kw)
        user = r.json()['headers']

        if not user:
            raise ContentDoesNotExist(type='USER', name=principal)

        if error_if_ambiguous:
            if len(user) > 1:
                raise AmbiguousContentError(type='USER', name=principal)
            user = user[0]

        return user
