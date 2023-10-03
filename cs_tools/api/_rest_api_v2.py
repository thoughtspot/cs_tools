from __future__ import annotations

from typing import TYPE_CHECKING
from typing import List, Union
import logging

import httpx

from cs_tools.api._client import RESTAPIClient
from cs_tools.api._utils import UNDEFINED
from cs_tools.types import GUID, MetadataObjectType

if TYPE_CHECKING:
    Identifier = Union[GUID, str]

log = logging.getLogger(__name__)


class RESTAPIv2(RESTAPIClient):
    """
    Implementation of the REST API v2.
    """

    # ==================================================================================================================
    # VERSION CONTROL     ::  https://developers.thoughtspot.com/docs/rest-apiv2-reference#_version_control_beta
    # ==================================================================================================================

    def vcs_search_config(self, *, org_ids: List[Identifier] = UNDEFINED) -> httpx.Response:
        d = {"org_identifiers": org_ids}
        r = self.post("api/rest/2.0/vcs/git/config/search", data=d)
        return r

    def vcs_search_commits(
        self,
        *,
        metadata_guid: Identifier = UNDEFINED,
        metadata_type: MetadataObjectType = "LOGICAL_TABLE",
        branch: str = UNDEFINED,
        offset: int = UNDEFINED,
        batchsize: int = UNDEFINED,
    ) -> httpx.Response:
        d = {
            "metadata_identifiers": metadata_guid,
            "metadata_type": metadata_type,
            "branch_name": branch,
            "record_offset": offset,
            "record_size": batchsize
        }
        r = self.post("api/rest/2.0/vcs/git/commits/search", data=d)
        return r
