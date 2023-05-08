from typing import List
import logging

from cs_tools.types import RecordsFormat
from cs_tools import utils

from . import types

log = logging.getLogger(__name__)


def _validate_objects_exist(ts, data: List[RecordsFormat]) -> List[types.DeleteRecord]:
    """
    /metadata/delete WILL NOT fail on ValueError.

    As long as valid UUID4s are passed, and valid types are passed, the
    endpoint will happily return. If content does not exist, or if the
    wrong type for GUIDs is passed, ThoughtSpot will attempt to delete the
    objects.

    What this means is you could potentially delete an object you didn't
    mean to delete.. so this filters those objects out.

    This is a ThoughtSpot API limitation.
    """
    data = [types.DeleteRecord(**content) for content in data]

    answers = [content for content in data if content.object_type == "QUESTION_ANSWER_BOOK"]
    liveboards = [content for content in data if content.object_type == "PINBOARD_ANSWER_BOOK"]

    content_to_filter = (
        (answers, "QUESTION_ANSWER_BOOK"),
        (liveboards, "PINBOARD_ANSWER_BOOK"),
    )

    for (objects, content_type) in content_to_filter:
        for chunk in utils.chunks(objects, n=25):
            batch = list(chunk)
            r = ts.api.metadata_list(metadata_type=content_type, fetch_guids=[c.object_guid for c in batch])
            headers = r.json()["headers"]

            for content in batch:
                header = utils.find(lambda h: h["id"] == content.object_guid, headers)

                if header is not None:
                    content.object_name = header["name"]
                    continue

                log.warning(f"{content.object_guid} is not a {content_type}, removing it from the delete record..")

                try:
                    data.remove(content)
                except ValueError:
                    pass

    return data
