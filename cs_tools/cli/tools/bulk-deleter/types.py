from typing import Tuple
from dataclasses import dataclass
from cs_tools.types import GUID, StrEnum


class AcceptedObjectType(StrEnum):
    QUESTION_ANSWER_BOOK = "answer"
    PINBOARD_ANSWER_BOOK = "liveboard"
    answer = "QUESTION_ANSWER_BOOK"
    liveboard = "PINBOARD_ANSWER_BOOK"
    pinboard = "PINBOARD_ANSWER_BOOK"

    @property
    def system_type(self) -> str:
        return self.name if self.name.endswith("BOOK") else self.value

    def __eq__(self, other) -> bool:
        if hasattr(other, "value"):
            other = other.value

        return other in (self.value, self.name)


@dataclass
class DeleteRecord:
    """Represents an object to DELETE"""
    object_type: AcceptedObjectType
    object_guid: GUID
    object_name: str = None
    status: str = ":cross_mark:"

    def __post_init__(self):
        self.object_type = AcceptedObjectType[self.object_type].system_type

    @property
    def values(self) -> Tuple[str]:
        return self.status, AcceptedObjectType(self.object_type).name, self.object_guid, self.object_name
