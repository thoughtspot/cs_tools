from typing import List
import logging
import enum

import requests

from thoughtspot.models.base import APIBase, TSPublic
from thoughtspot.settings import APIParameters


_log = logging.getLogger(__name__)


class MetadataObject(enum.Enum):
    QUESTION_ANSWER_BOOK = 'QUESTION_ANSWER_BOOK'
    PINBOARD_ANSWER_BOOK = 'PINBOARD_ANSWER_BOOK'
    QUESTION_ANSWER_SHEET = 'QUESTION_ANSWER_SHEET'
    PINBOARD_ANSWER_SHEET = 'PINBOARD_ANSWER_SHEET'
    LOGICAL_COLUMN = 'LOGICAL_COLUMN'
    LOGICAL_TABLE = 'LOGICAL_TABLE'
    LOGICAL_RELATIONSHIP = 'LOGICAL_RELATIONSHIP'
    TAG = 'TAG'
    DATA_SOURCE = 'DATA_SOURCE'


class LogicalTableSubtype(enum.Enum):
    ONE_TO_ONE_LOGICAL = 'ONE_TO_ONE_LOGICAL'
    WORKSHEET = 'WORKSHEET'
    PRIVATE_WORKSHEET = 'PRIVATE_WORKSHEET'
    USER_DEFINED = 'USER_DEFINED'
    AGGR_WORKSHEET = 'AGGR_WORKSHEET'


class MetadataCategory(enum.Enum):
    ALL = 'ALL'
    MY = 'MY'
    FAVORITE = 'FAVORITE'
    REQUESTED = 'REQUESTED'


class SortOrder(enum.Enum):
    DEFAULT = 'DEFAULT'
    NAME = 'NAME'
    DISPLAY_NAME = 'DISPLAY_NAME'
    AUTHOR = 'AUTHOR'
    CREATED = 'CREATED'
    MODIFIED = 'MODIFIED'


#


class ListVizHeadersParameters(APIParameters):
    id: str


class ListObjectHeadersParameters(APIParameters):
    type: MetadataObject = MetadataObject.PINBOARD_ANSWER_BOOK
    subtypes: LogicalTableSubtype
    category: MetadataCategory = MetadataObject.ALL
    sort: SortOrder = SortOrder.DEFAULT
    sortascending: bool = None
    offset: int = -1
    batchsize: int = None
    tagname: List[str] = []
    pattern: str
    skipids: str
    fetchids: str
    auto_created: bool = None


class ListParameters(ListObjectHeadersParameters):
    ownertypes: LogicalTableSubtype


#

class PrivateMetadata(APIBase):
    """
    Metadata Services.
    """

    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/metadata'

    def list(self, **parameters) -> requests.Response:
        """
        List of metadata objects in the repository.
        """
        p = ListParameters(**parameters)
        r = self.get(f'{self.base_url}/listobjectheaders', params=p.dict())
        return r


class Metadata(TSPublic):
    """
    Public Metadata Services.
    """

    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/metadata'

    def list_viz_headers(self, **parameters) -> requests.Response:
        """
        Get the visualization headers from the ThoughtSpot system.
        """
        p = ListVizHeadersParameters(**parameters)
        r = self.post(f'{self.base_url}/listvizheaders', params=p.dict())
        return r

    def list_object_headers(self, **parameters) -> requests.Response:
        """
        List of metadata object headers in the repository.
        """
        p = ListObjectHeadersParameters(**parameters)
        r = self.post(f'{self.base_url}/listobjectheaders', params=p.dict())
        return r
