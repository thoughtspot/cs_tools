from __future__ import annotations

import logging
from typing import List, Union
from typing import TYPE_CHECKING

import httpx

from cs_tools.api._client import RESTAPIClient
from cs_tools.api._utils import UNDEFINED
from cs_tools.types import DeployType, DeployPolicy, GUID, MetadataObjectType

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

    def vcs_git_config_search(self, *, org_ids: List[Identifier] = UNDEFINED) -> httpx.Response:
        d = {"org_identifiers": org_ids}
        r = self.post("api/rest/2.0/vcs/git/config/search", data=d)
        return r

    def vcs_git_commits_search(
            self,
            *,
            metadata_identifier: Identifier = UNDEFINED,
            metadata_type: MetadataObjectType = UNDEFINED,
            branch: str = UNDEFINED,
            offset: int = 0,
            batchsize: int = -1,
    ) -> httpx.Response:
        d = {
            "metadata_identifier": metadata_identifier,
            "metadata_type": metadata_type,
            "branch_name": branch,
            "record_offset": offset,
            "record_size": batchsize
        }
        r = self.post("api/rest/2.0/vcs/git/commits/search", data=d)
        return r

    def vcs_git_config_create(self,
                              *,
                              repository_url: str,
                              username: str,
                              access_token: str,
                              org_identifier: Identifier,
                              branch_names: List[str] = UNDEFINED,
                              default_branch_name: str = UNDEFINED,
                              enable_guid_mapping: bool = False,
                              guid_mapping_branch_name: str
                              ) -> httpx.Response:
        d = {
            "repository_url": repository_url,
            "username": username,
            "access_token": access_token,
            "org_identifier": org_identifier,
            "branch_names": branch_names,
            "default_branch_name": default_branch_name,
            "enable_guid_mapping": enable_guid_mapping,
            "guid_mapping_branch_name": guid_mapping_branch_name
        }
        r = self.post("api/rest/2.0/vcs/git/config/create", data=d)
        return r

    def vcs_git_config_update(self,
                              *,
                              repository_url: str,
                              username: str,
                              access_token: str,
                              org_identifier: Identifier = UNDEFINED,
                              branch_names: List[str] = UNDEFINED,
                              default_branch_name: str = UNDEFINED,
                              enable_guid_mapping: bool = False,
                              guid_mapping_branch_name: str = UNDEFINED
                              ) -> httpx.Response:
        d = {
            "repository_url": repository_url,
            "username": username,
            "access_token": access_token,
            "org_identifier": org_identifier,
            "branch_names": branch_names,
            "default_branch_name": default_branch_name,
            "enable_guid_mapping": enable_guid_mapping,
            "guid_mapping_branch_name": guid_mapping_branch_name
        }
        r = self.post("api/rest/2.0/vcs/git/config/update", data=d)
        return r

    def vcs_git_config_delete(self, *, cluster_level: bool = False) -> httpx.Response:
        d = {
            "cluster_level": cluster_level
        }
        r = self.post("api/rest/2.0/vcs/git/config/delete", data=d)
        return r

    def vcs_git_branches_commit(self,
                                *,
                                metadata: List[Identifier],
                                branch_name: str = UNDEFINED,
                                comment: str
                                ) -> httpx.Response:
        d = {
            metadata: metadata,
            "branch_name": branch_name,
            "comment": comment
        }
        r = self.post("api/rest/2.0/vcs/git/branches/commit", data=d)
        return r

    def vcs_git_commits_id_revert(self,
                                  *,
                                  commit_id: str,
                                  metadata: List[Identifier],
                                  branch_name: str,
                                  revert_policy: DeployPolicy = DeployPolicy.all_or_none
                                  ) -> httpx.Response:
        d = {
            "commit_id": commit_id,
            "metadata": metadata,
            "branch_name": branch_name,
            "revert_policy": revert_policy
        }
        r = self.post(f"api/rest/2.0/vcs/git/commits/{id}/revert", data=d)
        return r

    def vcs_git_branches_validate(self,
                                  *,
                                  source_branch_name: str,
                                  target_branch_name: str,
                                  ) -> httpx.Response:
        d = {
            "source_branch_name": source_branch_name,
            "target_branch_name": target_branch_name,
        }
        r = self.post("api/rest/2.0/vcs/git/branches/validate", data=d)
        return r

    def vcs_git_commits_deploy(self, *,
                               commit_id: str,
                               branch_name: str,
                               deploy_type: DeployType = DeployType.delta,
                               deploy_policy: DeployPolicy = DeployPolicy.all_or_none
                               ) -> httpx.Response:
        d = {
            "commit_id": commit_id,
            "branch_name": branch_name,
            "deploy_type": deploy_type,
            "deploy_policy": deploy_policy
        }
        r = self.post("api/rest/2.0/vcs/git/commits/deploy", data=d)
        return r
