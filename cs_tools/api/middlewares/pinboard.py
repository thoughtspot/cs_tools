from typing import Any, Dict, List, Union
import logging

from pydantic import validate_arguments

from cs_tools.data.enums import MetadataCategory
from cs_tools.errors import ContentDoesNotExist


log = logging.getLogger(__name__)


class PinboardMiddleware:
    """
    """
    def __init__(self, ts):
        self.ts = ts

    @validate_arguments
    def all(
        self,
        *,
        tags: Union[str, List[str]] = None,
        category: MetadataCategory = MetadataCategory.all,
        exclude_system_content: bool = True,
        chunksize: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Get all pinboards in ThoughtSpot.

        Parameters
        ----------
        tags : str, or list of str
          pinboards which are specifically tagged or stickered

        category : str = 'all'
          one of: 'all', 'yours', or 'favorites'

        exclude_system_content : bool = True
          whether or not to include system-generated pinboards

        Returns
        -------
        pinboards : List[Dict[str, Any]]
          all pinboard headers
        """
        if isinstance(tags, str):
            tags = [tags]

        offset = 0
        pinboards = []

        while True:
            r = self.ts.api._metadata.list(
                    type='PINBOARD_ANSWER_BOOK',
                    category=category,
                    tagname=tags,
                    batchsize=chunksize,
                    offset=offset
                )

            data = r.json()
            pinboards.extend(data['headers'])
            offset += len(data['headers'])

            if not data['headers'] and not pinboards:
                info = {
                    "incl": "exclude" if exclude_system_content else "include",
                    "category": category,
                    "tags": ", ".join(tags),
                    "reason": (
                        "Zero {type} matched the following filters"
                        "\n"
                        "\n  - [blue]{category.value}[/] {type}"
                        "\n  - [blue]{incl}[/] admin-generated {type}"
                        "\n  - with tags [blue]{tags}"
                    )
                }
                raise ContentDoesNotExist(type="pinboards", **info)

            if data['isLastBatch']:
                break

        if exclude_system_content:
            pinboards = [
                pinboard
                for pinboard in pinboards
                if pinboard['authorName'] not in ('system', 'tsadmin', 'su')
            ]

        return pinboards
