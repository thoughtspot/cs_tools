from __future__ import annotations

from typing import Any, List, Dict
from io import BufferedIOBase
import datetime as dt
import tempfile
import pathlib
import logging
import json
import time

import httpx

from cs_tools.api._utils import scrub_undefined, scrub_sensitive, dumps, UNDEFINED
from cs_tools._version import __version__
from cs_tools.types import (
    MetadataObjectSubtype,
    ShareModeAccessLevel,
    MetadataObjectType,
    ConnectionMetadata,
    SecurityPrincipal,
    MetadataCategory,
    TMLImportPolicy,
    PermissionType,
    ConnectionType,
    UserProfile,
    FormatType,
    TMLObject,
    SortOrder,
    TMLType,
    GUID,
    SharingVisibility,
    GroupPrivilege,
    GroupInfo,
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
                "x-requested-by": "CS Tools",
                "user-agent": f"cs_tools/{__version__} (+github: thoughtspot/cs_tools)"
            }
        )

    def request(self, method: str, endpoint: str, **request_kw) -> httpx.Response:
        """Make an HTTP request."""
        request_kw = scrub_undefined(request_kw)
        secure = scrub_sensitive(request_kw)

        log.debug(f">> {method.upper()} to {endpoint} with keywords {secure}")

        try:
            r = super().request(method, endpoint, **request_kw)
        except httpx.RequestError as e:
            log.debug("Something went wrong calling the ThoughtSpot API", exc_info=True)
            log.warning(f"Could not connect to your ThoughtSpot cluster: {e}")
            raise e from None

        log.debug(f"<< HTTP: {r.status_code}")

        if r.text:
            TRACE = 5
            log.log(TRACE, "<< CONTENT:\n\n%s", r.text)

        attempts = 0

        # exponential backoff to 3 attempts (4s, 16s, 64s)
        while r.status_code in (httpx.codes.GATEWAY_TIMEOUT, httpx.codes.BAD_GATEWAY):
            attempts += 1

            if attempts > 3:
                break

            backoff = 4 ** attempts
            log.warning(f"Your ThoughtSpot cluster didn't respond to '{method} {endpoint}', backing off for {backoff}s")
            time.sleep(backoff)
            r = super().request(method, endpoint, **request_kw)

        if r.is_error:
            r.raise_for_status()

        return r

    # ==================================================================================================================
    # SESSION     ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_session_management
    # ==================================================================================================================

    def _trusted_auth(self, *, username: str, secret: GUID) -> httpx.Response:
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
        r = self.put("callosum/v1/tspublic/v1/session/orgs", data=d)
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
        self, *, org_id: int = UNDEFINED, org_name: str = UNDEFINED, show_inactive: bool = False
    ) -> httpx.Response:
        d = {"id": org_id, "name": org_name, "showinactive": show_inactive, "orgScope": "ALL"}
        r = self.post("callosum/v1/tspublic/v1/org/search", data=d)
        return r

    # ==================================================================================================================
    # USER        ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_user_management
    # ==================================================================================================================

    def user_create(
        self,
        *,
        username: str,
        email: str,
        display_name: str,
        password: str,
        sharing_visibility: SharingVisibility = "DEFAULT",
        user_type: str = "LOCAL_USER",
        user_properties: Dict[str, Any] = UNDEFINED,
        group_guids: List[GUID] = UNDEFINED,
        # org_id: int = UNDEFINED,
    ) -> httpx.Response:
        d = {
            "name": username,
            "email": email,
            "displayname": display_name,
            "password": password,
            "visibility": sharing_visibility,
            "usertype": user_type,
            "properties": user_properties,
            "groups": dumps(group_guids),
            "triggeredbyadmin": True,
        }
        r = self.post("callosum/v1/tspublic/v1/user", data=d)
        return r

    def user_read(self, *, user_guid: GUID = UNDEFINED, username: str = UNDEFINED) -> httpx.Response:
        p = {"userid": user_guid, "name": username}
        r = self.get("callosum/v1/tspublic/v1/user", params=p)
        return r

    def user_update(self, *, user_guid: GUID, content: UserProfile, password: str = UNDEFINED) -> httpx.Response:
        d = {"userid": user_guid, "content": json.dumps(content), "password": password, "triggeredbyadmin": True}
        r = self.put(f"callosum/v1/tspublic/v1/user/{user_guid}", data=d)
        return r

    def user_list(self) -> httpx.Response:
        r = self.get("callosum/v1/tspublic/v1/user/list")
        return r

    def user_transfer_ownership(
        self, *, from_username: str, to_username: str, object_guids: List[GUID] = UNDEFINED
    ) -> httpx.Response:
        p = {"fromUserName": from_username, "toUserName": to_username, "objectsID": dumps(object_guids)}
        r = self.post("callosum/v1/tspublic/v1/user/transfer/ownership", params=p)
        return r

    def user_sync(
        self,
        *,
        principals: List[SecurityPrincipal],
        apply_changes: bool = False,
        remove_deleted: bool = True,
        password: str = UNDEFINED,
    ) -> httpx.Response:
        fp = pathlib.Path(tempfile.gettempdir()) / f"principals-{dt.datetime.now():%Y%m%dT%H%M%S}.json"
        fp.write_text(json.dumps(principals, indent=4))

        try:
            f = {"principals": ("principals.json", fp.open("rb"), "application/json")}
            d = {"applyChanges": apply_changes, "removeDeleted": remove_deleted, "password": password}
            r = self.post("callosum/v1/tspublic/v1/user/sync", files=f, data=d)

        finally:
            fp.unlink()

        return r

    # ==================================================================================================================
    # GROUP       ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_groups_and_privileges
    # ==================================================================================================================

    def group_create(
        self,
        *,
        group_name: str,
        display_name: str,
        description: str = None,
        privileges: List[GroupPrivilege],
        sharing_visibility: SharingVisibility = "DEFAULT",
        group_type: str = "LOCAL_GROUP",
    ) -> httpx.Response:
        d = {
            "name": group_name,
            "display_name": display_name,
            "description": description,
            "privileges": dumps(privileges),
            "visibility": sharing_visibility,
            "grouptype": group_type,
        }
        r = self.post("callosum/v1/tspublic/v1/group", data=d)
        return r

    def group_read(self, *, group_guid: GUID = UNDEFINED, group_name: str = UNDEFINED) -> httpx.Response:
        p = {"groupid": group_guid, "name": group_name}
        r = self.get("callosum/v1/tspublic/v1/group", params=p)
        return r

    def group_update(self, *, group_guid: GUID, content: GroupInfo) -> httpx.Response:
        d = {"groupid": group_guid, "content": json.dumps(content), "triggeredbyadmin": True}
        r = self.put(f"callosum/v1/tspublic/v1/group/{group_guid}", data=d)
        return r

    def group_list_users(self, *, group_guid: GUID) -> httpx.Response:
        r = self.get(f"callosum/v1/tspublic/v1/group/{group_guid}/users")
        return r

    def group_add_user(self, *, group_guid: GUID, user_guid: GUID) -> httpx.Response:
        d = {"groupid": group_guid, "userid": user_guid}
        r = self.post(f"callosum/v1/tspublic/v1/group/{group_guid}/user/{user_guid}", data=d)
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
            "formattpe": format_type,
        }
        r = self.post("callosum/v1/tspublic/v1/searchdata", params=p)
        return r

    # ==================================================================================================================
    # METADATA    ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_metadata_management
    # ==================================================================================================================

    def metadata_assign_tag(
        self,
        *,
        metadata_guids: List[GUID],
        metadata_types: List[MetadataObjectType],
        tag_guids: List[GUID] = UNDEFINED,
        tag_names: List[str] = UNDEFINED,
    ) -> httpx.Response:
        d = {
            "id": dumps(metadata_guids),
            "type": dumps(metadata_types),
            "tagid": dumps(tag_guids),
            "tagname": dumps(tag_names),
        }
        r = self.post("callosum/v1/tspublic/v1/metadata/assigntag", data=d)
        return r

    def metadata_unassign_tag(
        self,
        *,
        metadata_guids: List[GUID],
        metadata_types: List[MetadataObjectType],
        tag_guids: List[GUID] = UNDEFINED,
        tag_names: List[str] = UNDEFINED,
    ) -> httpx.Response:
        d = {
            "id": dumps(metadata_guids),
            "type": dumps(metadata_types),
            "tagid": dumps(tag_guids),
            "tagname": dumps(tag_names),
        }
        r = self.post("callosum/v1/tspublic/v1/metadata/unassigntag", data=d)
        return r

    def metadata_list(
        self,
        *,
        metadata_type: MetadataObjectType = "QUESTION_ANSWER_BOOK",
        subtypes: List[MetadataObjectSubtype] = UNDEFINED,
        owner_types: List[MetadataObjectType] = UNDEFINED,
        category: MetadataCategory = "ALL",
        sort: SortOrder = "DEFAULT",
        sort_ascending: bool = UNDEFINED,
        offset: int = -1,
        batchsize: int = UNDEFINED,
        tag_names: List[str] = UNDEFINED,
        pattern: str = UNDEFINED,
        show_hidden: bool = False,
        skip_guids: List[GUID] = UNDEFINED,
        fetch_guids: List[GUID] = UNDEFINED,
        auto_created: bool = False,
        author_guid: GUID = UNDEFINED,
    ) -> httpx.Response:
        p = {
            "type": metadata_type,
            "subtypes": dumps(subtypes),
            "ownertypes": dumps(owner_types),
            "category": category,
            "sort": sort,
            "sortascending": sort_ascending,
            "offset": offset,
            "batchsize": batchsize,
            "tagname": dumps(tag_names),
            "pattern": pattern,
            "showhidden": show_hidden,
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
        guids: List[GUID],
        metadata_type: MetadataObjectType = "LOGICAL_TABLE",
        show_hidden: bool = False,
    ) -> httpx.Response:
        p = {
            "type": metadata_type,
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
        export_guids: List[GUID],
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
        import_objects: List[TMLObject],
        import_policy: TMLImportPolicy = "VALIDATE_ONLY",
        force_create: bool = False,
    ) -> httpx.Response:
        d = {"import_objects": dumps(import_objects), "import_policy": import_policy, "force_create": force_create}
        r = self.post("callosum/v1/tspublic/v1/metadata/tml/import", data=d)
        return r

    # ==================================================================================================================
    # CONNECTION  ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_data_connections
    # ==================================================================================================================

    def connection_fetch_connection(
        self,
        *,
        guid: GUID,
        include_columns: bool = False,
        config: ConnectionMetadata = UNDEFINED,
        authentication_type: str = "SERVICE_ACCOUNT"
    ) -> httpx.Response:
        d = {
            "id": guid,
            "includeColumns": include_columns,
            "config": config,
            "authentication_type": authentication_type
        }
        r = self.post("callosum/v1/tspublic/v1/connection/fetchConnection", data=d)
        return r

    def connection_fetch_live_columns(
        self,
        *,
        guid: GUID,
        tables: List[Dict[str, Any]] = UNDEFINED,
        config: ConnectionMetadata = UNDEFINED,
        authentication_type: str = "SERVICE_ACCOUNT"
    ) -> httpx.Response:
        d = {
            "connection_id": guid,
            "tables": dumps(tables),
            "config": config,
            "authentication_type": authentication_type
        }
        r = self.post("callosum/v1/connection/fetchLiveColumns", data=d)
        return r

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
        r = self.post("callosum/v1/tspublic/v1/connection/update", data=d)
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
        guids: List[str],
        metadata_type: MetadataObjectType = "LOGICAL_TABLE",
        batchsize: int = -1,
        offset: int = -1,
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
        guids: List[GUID],
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
        permissions: Dict[GUID, ShareModeAccessLevel],
    ) -> httpx.Response:
        d = {
            "type": metadata_type,
            "id": dumps(guids),
            "permission": {
                "permissions": {
                    principal_guid: {"shareMode": access_level.value} for principal_guid, access_level in permissions.items()
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
        guids: List[GUID],
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
        fullpath = self.dataservice_url.copy_with(path="/ts_dataservice/v1/public/session")
        d = {"username": username, "password": password}
        r = self.post(fullpath, data=d)
        return r

    def dataservice_dataload_initialize(self, *, data: Any, timeout: float = UNDEFINED) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path="/ts_dataservice/v1/public/loads")
        timeout = self.timeout if timeout is UNDEFINED else timeout
        r = self.post(fullpath, timeout=timeout, json=data)
        return r

    def dataservice_dataload_start(
        self, *, cycle_id: GUID, fd: BufferedIOBase | Any, timeout: float = UNDEFINED
    ) -> httpx.Response:
        # This endpoint returns immediately once the file uploads to the remote host.
        # Processing of the dataload happens concurrently, and this function may be
        # called multiple times to paralellize the full data load across multiple files.
        fullpath = self.dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}")
        timeout = self.timeout if timeout is UNDEFINED else timeout
        r = self.post(fullpath, timeout=timeout, files={"upload-file": fd})
        return r

    def dataservice_dataload_commit(self, *, cycle_id: GUID) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}/commit")
        r = self.post(fullpath)
        return r

    def dataservice_dataload_status(self, *, cycle_id: GUID) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}")
        r = self.get(fullpath)
        return r

    def dataservice_dataload_bad_records(self, *, cycle_id: GUID) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}/bad_records_file")
        r = self.get(fullpath)
        return r
