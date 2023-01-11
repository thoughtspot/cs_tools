from __future__ import annotations
from typing import Any
from io import BuffedIOBase
import datetime as dt
import logging
import pathlib
import json

import httpx

from cs_tools.api._utils import UNDEFINED, dumps, scrub_undefined, scrub_sensitive
from cs_tools._version import __version__
from cs_tools.types import GUID
from cs_tools.types import UserProfile, SecurityPrincipal, TMLObject
from cs_tools.types import (
    ConnectionMetadata,
    ConnectionType,
    FormatType,
    MetadataCategory,
    MetadataObjectType,
    MetadataObjectSubtype,
    PermissionType,
    ShareModeAccessLevel,
    SortOrder,
    TMLType,
    TMLImportPolicy,
)

log = logging.getLogger(__name__)


class RESTAPIv1(httpx.Client):
    """
    Implementation of the REST API v1.
    """

    def __init__(self, ts_url: str, **client_opts):
        client_opts["base_url"] = ts_url
        super().__init__(**client_opts)
        # DEV NOTE: @boonhapus 2023/01/08
        #    these are enforced client settings regardless of API call
        #
        #    TIMEOUT = 15 minutes
        #    HEADERS = metadata about requests sent to the ThoughtSpot server
        #
        self.timeout = 15 * 60
        self.headers.update(
            {
                "x-requested-by": "ThoughtSpot",
                "user-agent": f"cs_tools/{__version__} (+github: thoughtspot/cs_tools)"
            }
        )

        # TSLOAD dataservice is sitting behind a load balancer on port 8442
        self._dataservice_url = self.base_url.copy_with(port=8442)

    def request(self, method: str, endpoint: str, **request_kw) -> httpx.Response:
        """Make an HTTP request."""
        request_kw = scrub_undefined(request_kw)
        secure = scrub_sensitive(request_kw)

        log.debug(f">> {method.upper()} to {endpoint} with keywords {secure}")

        r = super().request(method, endpoint, **request_kw)
        r.raise_for_status()

        log.debug(f'<< HTTP: {r.status_code}')

        if r.text:
            log.trace('<< CONTENT:\n\n%s', r.text)

        return r

    # ==================================================================================================================
    # SESSION     ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_session_management
    # ==================================================================================================================

    def _token_auth(self, *, username: str, secret: GUID) -> httpx.Response:
        # get the login token for a given user
        d = {"secret_key": secret, "username": username, "access_level": "FULL"}
        r = self.post("callosum/v1/tspublic/v1/session/auth/token", data=d)

        # establish a session as that user, using the token
        d = {"auth_token": r.text, "username": username}
        r = self.post("callosum/v1/tspublic/v1/session/login/token", data=d)
        return r

    def session_login(self, *, username: str, password: str) -> httpx.Response:
        d = {"username": username, "password": password}
        r = self.post("callosum/v1/tspublic/v1/session/login", data=d)
        return r

    def session_logout(self) -> httpx.Response:
        r = self.post("callosum/v1/tspublic/v1/session/logout")
        return r

    def session_orgs_read(self) -> httpx.Response:
        p = {"batchsize": -1, "offset": -1}
        r = self.get("callosum/v1/tspublic/v1/session/orgs", params=p)
        return r

    def session_orgs_update(self, *, org_id: int) -> httpx.Response:
        d = {"orgid": org_id}
        r = self.put("callosum/v1/tspublic/v1/session/org", data=d)
        return r

    def session_info(self) -> httpx.Response:
        r = self.get("callosum/v1/tspublic/v1/session/info")
        return r

    # ==================================================================================================================
    # ORG         ::  NOT YET SET
    # ==================================================================================================================

    def org_read(self, *, org_id: int = UNDEFINED, org_name: str = UNDEFINED) -> httpx.Response:
        p = {"id": org_id, "name": org_name, "orgScope": "ALL"}
        r = self.get("callosum/v1/tspublic/v1/org", params=p)
        return r

    def org_search(
        self,
        *,
        org_id: int = UNDEFINED,
        org_name: str = UNDEFINED,
        show_inactive: bool = False
    ) -> httpx.Response:
        d = {"id": org_id, "name": org_name, "showinactive": show_inactive, "orgScope": "ALL"}
        r = self.post("callosum/v1/tspublic/v1/org/search", data=d)
        return r

    # ==================================================================================================================
    # USER        ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_user_management
    # ==================================================================================================================

    def user_read(self, *, user_guid: GUID = UNDEFINED, name: str = UNDEFINED) -> httpx.Response:
        p = {"userid": user_guid, "name": name}
        r = self.get("callosum/v1/tspublic/v1/user", params=p)
        return r

    def user_update(self, *, user_guid: GUID, content: UserProfile, password: str = UNDEFINED) -> httpx.Response:
        d = {"userid": user_guid, "content": content, "password": password}
        r = self.put(f"callosum/v1/tspublic/v1/user/{user_guid}", data=d)
        return r

    def user_list(self) -> httpx.Response:
        r = self.get("callosum/v1/tspublic/v1/user/list")
        return r

    def user_transfer_ownership(
        self,
        *,
        from_username: str,
        to_username: str,
        object_guids: list[GUID] = UNDEFINED
    ) -> httpx.Response:
        p = {"fromUserName": from_username, "toUserName": to_username, "objectsID": dumps(object_guids)}
        r = self.post("callosum/v1/tspublic/v1/user/transfer/ownership", params=p)
        return r

    def user_sync(
        self,
        *,
        principals: list[SecurityPrincipal],
        apply_changes: bool = False,
        remove_deleted: bool = True,
        password: str = UNDEFINED
    ) -> httpx.Response:
        fp = pathlib.Path(f"principals-{dt.datetime.now():%Y%m%dT%H%M%S}.json")
        fp.write_text(json.dumps(principals, indent=4))

        f = {"principals": ("principals.json", fp.open("rb"), "application/json")}
        p = {"applyChanges": apply_changes, "removeDeleted": remove_deleted, "password": password}
        r = self.post("callosum/v1/tspublic/v1/user/transfer/ownership", files=f, params=p)
        return r

    # ==================================================================================================================
    # GROUP       ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_groups_and_privileges
    # ==================================================================================================================

    def group_read(self, *, group_guid: GUID = UNDEFINED, name: str = UNDEFINED) -> httpx.Response:
        p = {"groupid": group_guid, "name": name}
        r = self.get("callosum/v1/tspublic/v1/group", params=p)
        return r

    # ==================================================================================================================
    # DATA        ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_groups_and_privileges
    # ==================================================================================================================

    def search_data(
        self,
        *,
        query_string: str,
        data_source_guid: str,
        batchsize: int = -1,
        page_number: int = -1,
        offset: int = -1,
        format_type: FormatType = "COMPACT",
    ) -> httpx.Response:
        p = {
            "query_string": query_string,
            "data_source_guid": data_source_guid,
            "batchsize": batchsize,
            "pagenumber": page_number,
            "offset": offset,
            "formattpe": format_type
        }
        r = self.post("callosum/v1/tspublic/v1/searchdata", params=p)
        return r

    # ==================================================================================================================
    # METADATA    ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_metadata_management
    # ==================================================================================================================

    def metadata_assign_tag(
        self,
        *,
        metadata_guid: list[GUID],
        metadata_type: list[MetadataObjectType],
        tag_guids: list[GUID] = UNDEFINED,
        tag_names: list[str] = UNDEFINED,
    ) -> httpx.Response:
        d = {
            "id": dumps(metadata_guid),
            "type": dumps(metadata_type),
            "tagid": dumps(tag_guids),
            "tagname": dumps(tag_names),
        }
        r = self.post("callosum/v1/tspublic/v1/metadata/assigntag", data=d)
        return r

    def metadata_unassign_tag(
        self,
        *,
        metadata_guid: list[GUID],
        metadata_type: list[MetadataObjectType],
        tag_guids: list[GUID] = UNDEFINED,
        tag_names: list[str] = UNDEFINED,
    ) -> httpx.Response:
        d = {
            "id": dumps(metadata_guid),
            "type": dumps(metadata_type),
            "tagid": dumps(tag_guids),
            "tagname": dumps(tag_names),
        }
        r = self.post("callosum/v1/tspublic/v1/metadata/unassigntag", data=d)
        return r

    def metadata_list(
        self,
        *,
        metadata_type: MetadataObjectType = "QUESTION_ANSWER_BOOK",
        subtypes: list[MetadataObjectSubtype] = UNDEFINED,
        category: MetadataCategory = "ALL",
        sort: SortOrder = "DEFAULT",
        sort_ascending: bool = UNDEFINED,
        offset: int = -1,
        batchsize: int = UNDEFINED,
        tag_name: list[str] = UNDEFINED,
        pattern: str = UNDEFINED,
        skip_guids: list[GUID] = UNDEFINED,
        fetch_guids: list[GUID] = UNDEFINED,
        auto_created: bool = UNDEFINED,
        author_guid: GUID = UNDEFINED,
    ) -> httpx.Response:
        p = {
            "type": type,
            "subtypes": dumps(subtypes),
            "category": category,
            "sort": sort,
            "sortascending": sort_ascending,
            "offset": offset,
            "batchsize": batchsize,
            "tagname": dumps(tag_name),
            "pattern": pattern,
            "skipids": dumps(skip_guids),
            "fetchids": dumps(fetch_guids),
            "auto_created": auto_created,
            "authorguid": author_guid,
        }
        r = self.get("callosum/v1/tspublic/v1/metadata/list", params=p)
        return r

    def metadata_details(
        self,
        *,
        guids: list[GUID],
        metadata_type: MetadataObjectType = "LOGICAL_TABLE",
        show_hidden: bool = False,
    ) -> httpx.Response:
        p = {
            "type": type,
            "id": dumps(guids),
            "showhidden": show_hidden,
            "dropquestiondetails": False,
            "version": -1,
        }
        r = self.get("callosum/v1/tspublic/v1/metadata/details", params=p)
        return r

    def metadata_tml_export(
        self,
        *,
        export_guids: list[GUID],
        format_type: TMLType = "YAML",
        export_associated: bool = False,
        export_fqn: bool = True,  # this is a happier default
    ) -> httpx.Response:
        d = {
            "export_ids": dumps(export_guids),
            "formattype": format_type,
            "export_associated": export_associated,
            "export_fqn": export_fqn,
        }
        r = self.post("callosum/v1/tspublic/v1/metadata/tml/export", data=d)
        return r

    def metadata_tml_import(
        self,
        *,
        import_objects: list[TMLObject],
        import_policy: TMLImportPolicy = "VALIDATE_ONLY",
        force_create: bool = False,
    ) -> httpx.Response:
        d = {"import_objects": dumps(import_objects), "import_policy": import_policy, "force_create": force_create}
        r = self.post("callosum/v1/tspublic/v1/metadata/tml/import", data=d)
        return r

    # ==================================================================================================================
    # CONNECTION  ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_data_connections
    # ==================================================================================================================

    def connection_create(
        self,
        *,
        name: str,
        description: str,
        external_database_type: ConnectionType,
        create_empty: bool = False,
        metadata: ConnectionMetadata = UNDEFINED,
    ) -> httpx.Response:
        d = {
            "name": name,
            "description": description,
            "type": external_database_type,
            "createEmpty": create_empty,
            "metadata": metadata,
            # state  # inaccesible to the Developer
        }
        r = self.post("callosum/v1/tspublic/v1/connection/create", data=d)
        return r

    def connection_update(
        self,
        *,
        guid: GUID,
        name: str,
        description: str,
        external_database_type: ConnectionType,
        create_empty: bool = False,
        metadata: ConnectionMetadata = UNDEFINED,
    ) -> httpx.Response:
        d = {
            "name": name,
            "description": description,
            "type": external_database_type,
            "createEmpty": create_empty,
            "metadata": metadata,
            # state  # inaccesible to the Developer
        }
        r = self.post("callosum/v1/tspublic/v1/connection/create", data=d)
        return r

    def connection_export(self, *, guid: GUID) -> httpx.Response:
        p = {"id": guid}
        r = self.get("callosum/v1/tspublic/v1/connection/export", params=p)
        return r

    # ==================================================================================================================
    # DEPENDENCY  ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_dependent_objects
    # ==================================================================================================================

    def dependency_list_dependents(
        self,
        *,
        guids: list[str],
        metadata_type: MetadataObjectType = "LOGICAL_TABLE",
        batchsize: int = -1,
        offset: int = -1
    ) -> httpx.Response:
        d = {"type": metadata_type, "id": dumps(guids), "batchsize": batchsize, "offset": offset}
        r = self.post("callosum/v1/tspublic/v1/dependency/listdependents", data=d)
        return r

    # ==================================================================================================================
    # SECURITY    ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_security
    # ==================================================================================================================

    def security_share(
        self,
        *,
        metadata_type: str,
        guids: list[GUID],
        # DEV NOTE: @boonhapus 2023/01/09
        #    this parameter deviates from the REST API V1 contract!
        #
        #    the contract expects "permission" to look like..
        #
        #    "permission": {
        #        "permissions": {
        #            <user-or-group-guid-to-share-to>: {
        #                "shareMode": <access-level>
        #            },
        #            <user-or-group-guid-to-share-to>: {
        #                "shareMode": <access-level>
        #            },
        #            ...
        #        }
        #    }
        #
        #    we'll supply the data in the grandchild format for ease of use.
        #
        permissions: dict[GUID, ShareModeAccessLevel],
    ) -> httpx.Response:
        d = {
            "type": metadata_type,
            "id": dumps(guids),
            "permission": {
                "permissions": {
                    principal_guid: {
                        "shareMode": access_level
                    }
                    for principal_guid, access_level in permissions.items()
                }
            },
            # we don't support these options
            "emailshares": UNDEFINED,
            "notify": UNDEFINED,
            "message": UNDEFINED,
        }
        r = self.post("callosum/v1/tspublic/v1/security/share", data=d)
        return r

    def security_metadata_permissions(
        self,
        *,
        metadata_type: MetadataObjectType,
        guids: list[GUID],
        dependent_share: bool = False,
        permission_type: PermissionType = "DEFINED",
    ) -> httpx.Response:
        p = {
            "type": metadata_type,
            "id": dumps(guids),
            "dependentshare": dependent_share,
            "permissiontype": permission_type,
        }
        r = self.get("callosum/v1/tspublic/v1/security/metadata/permissions", params=p)
        return r

    # ==================================================================================================================
    # PERISCOPE (falcon monitor)
    # ==================================================================================================================

    def periscope_sage_table_info(self, *, nodes: str = "all") -> httpx.Response:
        p = {"nodes": nodes, "callosumTimeout": 600}  # override callosum timeouts to 10mins
        r = self.get("periscope/sage/combinedtableinfo", params=p)
        return r

    # ==================================================================================================================
    # THOUGHTSPOT DATASERVICE (tql, remote tsload API)
    # ==================================================================================================================

    @property
    def dataservice_url(self) -> httpx.URL:
        if hasattr(self, "_redirected_url_due_to_tsload_load_balancer"):
            url = self._redirected_url_due_to_tsload_load_balancer
        else:
            url = self.base_url.copy_with(port=8442)

        return url

    def dataservice_tokens_static(self) -> httpx.Response:
        r = self.get("ts_dataservice/v1/public/tql/tokens/static")
        return r

    def dataservice_tokens_dynamic(self) -> httpx.Response:
        r = self.get("ts_dataservice/v1/public/tql/tokens/dynamic")
        return r

    def dataservice_query(self, *, data: Any, timeout: float = UNDEFINED) -> httpx.Response:
        # Further reading on what can be passed to `data`
        #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_inputoutput_structure
        #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_request_body
        timeout = self.timeout if timeout is UNDEFINED else timeout
        r = self.post("ts_dataservice/v1/public/tql/query", timeout=timeout, json=data)
        return r

    def dataservice_script(self, *, data: Any, timeout: float = UNDEFINED) -> httpx.Response:
        # Further reading on what can be passed to `data`
        #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_inputoutput_structure
        #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_request_body_2
        timeout = self.timeout if timeout is UNDEFINED else timeout
        r = self.post("ts_dataservice/v1/public/tql/script", timeout=timeout, json=data)
        return r

    def dataservice_dataload_session(self, *, username: str, password: str) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path="session")
        d = {"username": username, "password": password}
        r = self.post(fullpath, data=d)
        return r

    def dataservice_dataload_initialize(self, *, data: Any, timeout: float = UNDEFINED) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path="loads")
        timeout = self.timeout if timeout is UNDEFINED else timeout
        r = self.post(fullpath, timeout=timeout, json=data)
        return r

    def dataservice_dataload_start(
        self,
        *,
        cycle_id: GUID,
        fd: BuffedIOBase | Any,
        timeout: float = UNDEFINED
    ) -> httpx.Response:
        # This endpoint will return immediately once the file has loaded to the remote
        # network. Processing of the dataload may happen concurrently, and thus, this
        # function may be called multiple times to paralellize the full data load across
        # multiple files.
        fullpath = self.dataservice_url.copy_with(path=f"loads/{cycle_id}")
        timeout = self.timeout if timeout is UNDEFINED else timeout
        r = self.post(fullpath, timeout=timeout, files={"upload-file": fd})
        return r

    def dataservice_dataload_commit(self, *, cycle_id: GUID) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path=f"loads/{cycle_id}/commit")
        r = self.post(fullpath)
        return r

    def dataservice_dataload_status(self, *, cycle_id: GUID) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path=f"loads/{cycle_id}")
        r = self.get(fullpath)
        return r

    def dataservice_dataload_bad_records(self, *, cycle_id: GUID) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path=f"loads/{cycle_id}/bad_records_file")
        r = self.get(fullpath)
        return r
