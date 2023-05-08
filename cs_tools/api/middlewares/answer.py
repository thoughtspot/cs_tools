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


class AnswerMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    @validate_arguments
    def all(
        self,
        *,
        tags: Union[str, List[str]] = None,
        category: MetadataCategory = MetadataCategory.all,
        hidden: bool = False,
        auto_created: bool = False,
        exclude_system_content: bool = True,
        chunksize: int = 500,
    ) -> RecordsFormat:
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
        answers : list[Dict[str, Any]]
          all answer headers
        """
        if isinstance(tags, str):
            tags = [tags]

        answers = []

        while True:
            r = self.ts.api.metadata_list(
                metadata_type="QUESTION_ANSWER_BOOK",
                category=category,
                tag_names=tags or _utils.UNDEFINED,
                show_hidden=hidden,
                auto_created=auto_created,
                batchsize=chunksize,
                offset=len(answers),
            )

            data = r.json()
            to_extend = data["headers"]

            if exclude_system_content:
                to_extend = [answer for answer in to_extend if answer.get("authorName") not in _utils.SYSTEM_USERS]

            answers.extend([{"metadata_type": "QUESTION_ANSWER_BOOK", **answer} for answer in to_extend])

            if not answers:
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
