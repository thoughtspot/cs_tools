from typing import Union, List, Dict, Any
import logging

from pydantic import validate_arguments

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
    def get_group_id(self, name: str):
        """
        Returns the GUID for a group with the given name.
        :param name: Name of the group, like 'Administrator'
        """
        r = self.ts.api.group.get_group(name=name)
        info = r.json()
        return info["header"]["id"]
