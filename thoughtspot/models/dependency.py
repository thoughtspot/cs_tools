import logging
import enum

import requests

from thoughtspot.models.base import APIBase
from thoughtspot.settings import APIParameters


_log = logging.getLogger(__name__)


class MetadataObject(enum.Enum):
    PHYSICAL_COLUMN = 'PHYSICAL_COLUMN'
    PHYSICAL_TABLE = 'PHYSICAL_TABLE'
    LOGICAL_COLUMN = 'LOGICAL_COLUMN'
    LOGICAL_TABLE = 'LOGICAL_TABLE'
    LOGICAL_RELATIONSHIP = 'LOGICAL_RELATIONSHIP'


#


class ListDependentsParameters(APIParameters):
    type: MetadataObject = MetadataObject.LOGICAL_COLUMN
    id: str  # GUID
    batchsize: int = 0


#

class Dependency(APIBase):
    """
    Dependency Services.
    """

    def base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/dependency'

    def list_dependents(self, **parameters) -> requests.Response:
        """
        Metadata objects referencing given object.
        """
        p = ListDependentsParameters(**parameters)
        r = self.get(f'{self.base_url}/listdependents', params=p.dict())
        return r
