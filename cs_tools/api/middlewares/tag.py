from __future__ import annotations

from typing import Any, TYPE_CHECKING, Dict
import logging

from pydantic import validate_arguments

from cs_tools.errors import ContentDoesNotExist
from cs_tools.types import RecordsFormat
from cs_tools.api._utils import dumps
from cs_tools import utils

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


class TagMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    @validate_arguments
    def create(self, tag_name: str) -> Dict[str, Any]:
        """
        Create a new tag in ThoughtSpot.

        Parameters
        ----------
        tag_name : str
          name of the tag to create
        """
        r = self.ts.api.request("POST", "callosum/v1/metadata/create", data={"type": "TAG", "name": tag_name})
        return r.json()["header"]

    @validate_arguments
    def delete(self, tag_name: str) -> None:
        """
        Remove a tag from ThoughtSpot.

        Parameters
        ----------
        tag_name : str
          name of the tag to delete

        Raises
        ------
        ContentDoesNotExist
          raised when a tag does not exist
        """
        tag = self.get(tag_name)

        self.ts.api.request("POST", "callosum/v1/metadata/delete", data={"type": "TAG", "id": dumps([tag["id"]])})

    @validate_arguments
    def all(self) -> RecordsFormat:
        """
        Get all tags in ThoughtSpot.
        """
        tags = []

        while True:
            r = self.ts.api.metadata_list(metadata_type="TAG", batchsize=50, offset=len(tags))
            data = r.json()
            tags.extend(data["headers"])

            if data["isLastBatch"]:
                break

        return tags

    @validate_arguments
    def get(self, tag_name: str, *, create_if_not_exists: bool = False) -> Dict[str, Any]:
        """
        Find a tag in ThoughtSpot.

        Parameters
        ----------
        tag_name : str
          name of the tag to find

        create_if_not_exists: bool, defaut False
          whether or not to create a missing tag

        Raises
        ------
        ContentDoesNotExist
          raised when a tag does not exist and is not to be autocreated
        """
        tag = utils.find(lambda e: e["name"].casefold() == tag_name.casefold(), self.all())

        if create_if_not_exists and tag is None:
            tag = self.create(tag_name)

        if tag is None:
            raise ContentDoesNotExist(type="tag", reason=f"No tag found with the name [blue]{tag_name}")

        return tag
