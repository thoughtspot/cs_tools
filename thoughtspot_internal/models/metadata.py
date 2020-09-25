from typing import Union, List
import logging
import enum

from thoughtspot.settings import APIParameters
import requests

from thoughtspot_internal.models import TSPrivate


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
    subtypes: LogicalTableSubtype = None
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


#


class Metadata(TSPrivate):
    """
    Metadata Services.
    """

    @property
    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/metadata'

    # def details(self, **parameters) -> requests.Response:
    #     """
    #     """
    #     p = DetailsParameters(**parameters)
    #     r = self.post(f'{self.base_url}/details', params=p.json())

    def list(self, **parameters) -> requests.Response:
        """
        List of metadata objects in the repository.
        """
        p = ListParameters(**parameters)
        r = self.get(f'{self.base_url}/list', params=p.json())
        return r

    def listas(self, **parameters) -> requests.Response:
        """
        TODO
        """
        p = ListAsParameters(**parameters)
        r = self.get(f'{self.base_url}/listas', params=p.json())
        return r

    def detail(self, guid, **parameters) -> requests.Response:
        """
        TODO
        """
        p = DetailParameters(id=guid, **parameters)
        r = self.get(f'{self.base_url}/detail/{guid}', params=p.json())
        return r
