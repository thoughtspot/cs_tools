from typing import List
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
    type: MetadataObject = MetadataObject.PHYSICAL_COLUMN
    id: str  # GUIDs .. so technically this is an array of guids [<guid>, <guid>]
    batchsize: int = -1


#

class Dependency(APIBase):
    """
    Dependency Services.
    """

    @property
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
        r = self.post(f'{self.base_url}/listdependents', data=p.json())
        return r
