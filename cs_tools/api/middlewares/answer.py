from __future__ import annotations
from typing import Any
from typing import TYPE_CHECKING
import logging

from pydantic import validate_arguments

from cs_tools.errors import ContentDoesNotExist
from cs_tools.types import MetadataCategory

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)
RECORDS = list[dict[str, Any]]


class AnswerMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    @validate_arguments
    def all(
        self,
        *,
        tags: str | list[str] = None,
        category: MetadataCategory = MetadataCategory.all,
        exclude_system_content: bool = True,
        chunksize: int = 500,
    ) -> RECORDS:
        """
        Get all answers in ThoughtSpot.

        Parameters
        ----------
        tags : str, or list of str
          answers which are specifically tagged or stickered

        category : str = 'all'
          one of: 'all', 'yours', or 'favorites'

        exclude_system_content : bool = True
          whether or not to include system-generated answers

        Returns
        -------
        answers : list[dict[str, Any]]
          all answer headers
        """
        if isinstance(tags, str):
            tags = [tags]

        offset = 0
        answers = []

        while True:
            r = self.ts.api.metadata.list(
                type="QUESTION_ANSWER_BOOK", category=category, tagname=tags, batchsize=chunksize, offset=offset
            )

            data = r.json()
            to_extend = data["headers"]
            offset += len(to_extend)

            if exclude_system_content:
                to_extend = [
                    answer for answer in to_extend if answer.get("authorName") not in ("system", "tsadmin", "su")
                ]

            answers.extend(to_extend)

            if not to_extend and not answers:
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
                    ),
                }
                raise ContentDoesNotExist(type="answers", **info)

            if data["isLastBatch"]:
                break

        return answers
