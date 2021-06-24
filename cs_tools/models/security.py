import enum
import pydantic
import httpx
from typing import List

from cs_tools.settings import APIParameters
from cs_tools.models import TSPrivate


class ObjectType(enum.Enum):
    LOGICAL_TABLE = "LOGICAL_TABLE"                # tables, worksheets, views
    QUESTION_ANSWER_BOOK = "QUESTION_ANSWER_BOOK"  # answer
    PINBOARD_ANSWER_BOOK = "PINBOARD_ANSWER_BOOK"  # pinboard


class SharePermission(str, enum.Enum):
    MODIFY = "MODIFY"
    NO_ACCESS = "NO_ACCESS"
    READ_ONLY = "READ_ONLY"

    def __str__(self):
        return self.value


class ShareParameters(APIParameters):
    type: ObjectType = None
    id: str = None
    # permission: Dict[str, Dict[str, Dict[str, SharePermission]]] = {}
    permission: str = ""
    emailshares: List[pydantic.EmailStr] = []
    notify: bool = True
    message: str = ""

    # TODO is it possible to use util.to_array()?
    @pydantic.validator('id', pre=True)
    def _flatten_id_list(cls, v):
        if not isinstance(id, str):
            v = ",".join(v)
        return f"[{v}]"

    @pydantic.validator('permission', pre=True)
    def _inject_share_mode(cls, v):
        new_v = {}
        for group_id, permission in v.items():
            new_v[group_id] = {'shareMode': str(permission)}
        return str({'permissions': new_v})


class _Security(TSPrivate):
    """
    Security services.
    """

    @property
    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/security'

    def share(self, **parameters) -> httpx.Response:
        """
        List of metadata objects in the repository.
        """
        p = ShareParameters(**parameters)
        r = self.post(f'{self.base_url}/share', data=p.json())
        return r
