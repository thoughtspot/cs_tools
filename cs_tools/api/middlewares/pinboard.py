from __future__ import annotations

from typing import TYPE_CHECKING, List, Union
import logging

from pydantic import validate_arguments

from cs_tools.errors import ContentDoesNotExist
from cs_tools.types import MetadataCategory, RecordsFormat
from cs_tools.api import _utils

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


class PinboardMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    @validate_arguments
    def all(
        self,
        *,
        tags: Union[str, List[str]] = None,
        category: MetadataCategory = MetadataCategory.all,
        exclude_system_content: bool = True,
        chunksize: int = 500,
    ) -> RecordsFormat:
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
        pinboards : api._types.RECORDS
          all pinboard headers
        """
        if isinstance(tags, str):
            tags = [tags]

        if tags is None:
            tags = []

        pinboards = []

        while True:
            r = self.ts.api.metadata_list(
                metadata_type="PINBOARD_ANSWER_BOOK",
                category=category,
                tag_names=tags or _utils.UNDEFINED,
                batchsize=chunksize,
                offset=len(pinboards)
            )

            data = r.json()
            to_extend = data["headers"]

            if exclude_system_content:
                to_extend = [pinboard for pinboard in to_extend if pinboard.get("authorName") not in _utils.SYSTEM_USERS]

            pinboards.extend([{"metadata_type": "PINBOARD_ANSWER_BOOK", **pinboard} for pinboard in to_extend])

            if not pinboards:
                info = {
                    "incl": "exclude" if exclude_system_content else "include",
                    "category": category,
                    "tags": ", ".join(tags),
                    "reason": (
                        "Zero {type} matched the following filters"
                        "\n"
                        "\n  - [b blue]{category.value}[/] {type}"
                        "\n  - [b blue]{incl}[/] admin-generated {type}"
                        "\n  - with tags [b blue]{tags}"
                    ),
                }
                raise ContentDoesNotExist(type="liveboards", **info)

            if data["isLastBatch"]:
                break

        return pinboards
