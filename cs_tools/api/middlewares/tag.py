from typing import Any, Dict, List
import logging

from pydantic import validate_arguments

from cs_tools.errors import ContentDoesNotExist
from cs_tools import util


log = logging.getLogger(__name__)


class TagMiddleware:
    """
    """
    def __init__(self, ts):
        self.ts = ts

    @validate_arguments
    def create(self, tag_name: str) -> Dict[str, Any]:
        """
        Create a new tag in ThoughtSpot.

        Parameters
        ----------
        tag_name : str
          name of the tag to create

        Returns
        -------
        data : Dict[str, Any]
          tag header
        """
        r = self.ts.api._metadata.create(name=tag_name, type='TAG')
        return r.json()['header']

    @validate_arguments
    def delete(self, tag_name: str) -> None:
        """
        Remove a tag from ThoughtSpot.

        Parameters
        ----------
        tag_name : str
          name of the tag to delete

        Returns
        -------
        None; nothing

        Raises
        ------
        ContentDoesNotExist
          raised when a tag does not exist
        """
        tag = self.get(tag_name)
        self.ts.api._metadata.delete(type='TAG', id=[tag['id']])

    @validate_arguments
    def all(self) -> List[Dict[str, Any]]:
        """
        Get all tags in ThoughtSpot.

        Parameters
        ----------
        None

        Returns
        -------
        tags : List[Dict[str, Any]]
          all tag headers
        """
        offset = 0
        tags = []

        while True:
            r = self.ts.api._metadata.list(type='TAG', batchsize=50, offset=offset)
            data = r.json()
            tags.extend(data['headers'])
            offset += len(data['headers'])

            if data['isLastBatch']:
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

        Returns
        -------
        data : Dict[str, Any]
          tag header

        Raises
        ------
        ContentDoesNotExist
          raised when a tag does not exist and is not to be autocreated
        """
        # api parameter: 'pattern' doesn't work for tags
        r = self.ts.api._metadata.list(type='TAG')
        data = r.json()['headers']
        tag = util.find(lambda e: e['name'].casefold() == tag_name.casefold(), data)

        if create_if_not_exists and tag is None:
            tag = self.create(tag_name)

        if tag is None:
            raise ContentDoesNotExist(type='TAG', name=tag_name)

        return tag
