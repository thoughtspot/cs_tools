from typing import Any, Dict
import logging

from pydantic import validate_arguments

from cs_tools.errors import ContentDoesNotExist
from cs_tools import util


log = logging.getLogger(__name__)


class TagMiddlware:
    """
    """
    def __init__(self, ts):
        self.ts = ts

    @validate_arguments
    def create(self, tag_name: str) -> Dict[str, Any]:
        """
        Create a tag in ThoughtSpot.

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
    def get(self, tag_name: str, *, create_if_not_exists: bool=False) -> Dict[str, Any]:
        """
        Create a tag in ThoughtSpot.

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
        """
        r = self.ts.api._metadata.list(type='TAG')

        tag = util.find(
                  lambda e: e['name'].casefold() == tag_name.casefold(),
                  r.json()['headers']
              )

        if create_if_not_exists and tag is None:
            tag = self.create(tag_name)

        if tag is None:
            raise ContentDoesNotExist(type='TAG', name=tag_name)

        return tag
