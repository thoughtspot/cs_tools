from typing import Union, List
import logging
import enum

import pydantic
import httpx

from cs_tools.util.swagger import to_array
from cs_tools.settings import APIParameters
from cs_tools.models import TSPrivate, TSPublic


log = logging.getLogger(__name__)


class MetadataObject(enum.Enum):
    DATA_SOURCE = 'DATA_SOURCE'
    LOGICAL_COLUMN = 'LOGICAL_COLUMN'
    LOGICAL_RELATIONSHIP = 'LOGICAL_RELATIONSHIP'
    LOGICAL_TABLE = 'LOGICAL_TABLE'
    PINBOARD_ANSWER_SHEET = 'PINBOARD_ANSWER_SHEET'
    PINBOARD_ANSWER_BOOK = 'PINBOARD_ANSWER_BOOK'
    QUESTION_ANSWER_BOOK = 'QUESTION_ANSWER_BOOK'
    QUESTION_ANSWER_SHEET = 'QUESTION_ANSWER_SHEET'
    TAG = 'TAG'
    # not currently shown in the Swagger UI.
    USER_GROUP = 'USER_GROUP'
    USER = 'USER'


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


class MinimumAccessLevel(enum.Enum):
    NO_ACCESS = 'NO_ACCESS'
    READ_ONLY = 'READ_ONLY'
    MODIFY = 'MODIFY'


class PrincipalType(enum.Enum):
    USER = 'USER'
    USER_GROUP = 'USER_GROUP'


#


class ListVizHeadersParameters(APIParameters):
    id: str


class ListObjectHeadersParameters(APIParameters):
    type: Union[MetadataObject, None] = MetadataObject.PINBOARD_ANSWER_BOOK
    subtypes: List[LogicalTableSubtype] = None
    category: MetadataCategory = MetadataCategory.ALL
    sort: SortOrder = SortOrder.DEFAULT
    sortascending: bool = None
    offset: int = -1
    batchsize: int = None
    tagname: List[str] = []
    pattern: str = None
    showhidden: bool = False
    skipids: str = None
    fetchids: str = None
    auto_created: bool = None

    @pydantic.validator('subtypes')
    def stringify_the_array(cls, v):
        return to_array([_.value for _ in v])


class ListParameters(ListObjectHeadersParameters):
    ownertypes: LogicalTableSubtype = None


class ListAsParameters(APIParameters):
    offset: int = -1
    batchsize: int = None
    pattern: str = None
    principalid: str = None
    minimumaccesslevel: MinimumAccessLevel = MinimumAccessLevel.NO_ACCESS
    type: PrincipalType = PrincipalType.USER_GROUP


class DetailParameters(APIParameters):
    type: MetadataObject = None
    id: str
    showhidden: bool = False
    dropquestiondetails: bool = False
    inboundrequesttype: int = 10000
    doUpdate: bool = True


class ListColumnParameters(APIParameters):
    id: str
    showhidden: bool = False


#

class Metadata(TSPublic):
    """
    Public Metadata Services.
    """

    @property
    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/metadata'

    def list_viz_headers(self, **parameters) -> httpx.Response:
        """
        Get the visualization headers from the ThoughtSpot system.
        """
        p = ListVizHeadersParameters(**parameters)
        r = self.get(f'{self.base_url}/listvizheaders', params=p.json())
        return r

    def list_object_headers(self, **parameters) -> httpx.Response:
        """
        List of metadata object headers in the repository.
        """
        p = ListObjectHeadersParameters(**parameters)
        r = self.get(f'{self.base_url}/listobjectheaders', params=p.json())
        return r


#

class _Metadata(TSPrivate):
    """
    Metadata Services.
    """

    @property
    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/metadata'

    # def details(self, **parameters) -> httpx.Response:
    #     """
    #     """
    #     p = DetailsParameters(**parameters)
    #     r = self.post(f'{self.base_url}/details', params=p.json())

    def list(self, **parameters) -> httpx.Response:
        """
        List of metadata objects in the repository.
        """
        p = ListParameters(**parameters)
        r = self.get(f'{self.base_url}/list', params=p.json())
        return r

    def listas(self, **parameters) -> httpx.Response:
        """
        TODO
        """
        p = ListAsParameters(**parameters)
        r = self.get(f'{self.base_url}/listas', params=p.json())
        return r

    def detail(self, guid, **parameters) -> httpx.Response:
        """
        TODO
        """
        p = DetailParameters(id=guid, **parameters)
        r = self.get(f'{self.base_url}/detail/{guid}', params=p.json())
        return r

    def list_columns(self, guid, **parameters) -> httpx.Response:
        """
        TODO
        """
        p = ListColumnParameters(id=guid, **parameters)
        r = self.get(f'{self.base_url}/listcolumns/{guid}', params=p.json())
        return r
