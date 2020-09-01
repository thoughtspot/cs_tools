from typing import Union
import logging
import enum

import requests

from thoughtspot.settings import APIParameters

from cs_tools.models import TSPrivate


_log = logging.getLogger(__name__)


class MetadataObject(enum.Enum):
    PHYSICAL_COLUMN = 'PHYSICAL_COLUMN'
    PHYSICAL_TABLE = 'PHYSICAL_TABLE'
    LOGICAL_COLUMN = 'LOGICAL_COLUMN'
    LOGICAL_TABLE = 'LOGICAL_TABLE'
    LOGICAL_RELATIONSHIP = 'LOGICAL_RELATIONSHIP'


#

class ListDependentsParameters(APIParameters):
    type: Union[MetadataObject, None] = MetadataObject.PHYSICAL_COLUMN
    id: str  # GUIDs .. so technically this is an array of guids [<guid>, <guid>]
    batchsize: int = -1


#

class Dependency(TSPrivate):
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
