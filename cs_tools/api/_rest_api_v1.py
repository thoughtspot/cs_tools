from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
import datetime as dt
import json
import logging
import pathlib
import tempfile

from cs_tools.api import _utils

if TYPE_CHECKING:
    from io import BufferedIOBase

    import httpx

    from cs_tools.api._client import RESTAPIClient
    from cs_tools.types import (
        GUID,
        ConnectionMetadata,
        ConnectionType,
        FormatType,
        GroupInfo,
        GroupPrivilege,
        MetadataCategory,
        MetadataObjectSubtype,
        MetadataObjectType,
        PermissionType,
        SecurityPrincipal,
        ShareModeAccessLevel,
        SharingVisibility,
        SortOrder,
        TMLImportPolicy,
        TMLObject,
        TMLType,
        UserProfile,
    )

log = logging.getLogger(__name__)


class RESTAPIv1:
    """
    Implementation of the public REST API v1.

    Not all endpoints are defined.
    """

    def __init__(self, api_client: RESTAPIClient):
        self._api_client = api_client
        self._redirected_url_due_to_tsload_load_balancer: httpx.URL | None = None

    def request(self, method: str, endpoint: str, **request_kw) -> httpx.Response:
        """Pre-process the request to remove undefined parameters."""
        request_kw = _utils.scrub_undefined_sentinel(request_kw, null=_utils.UNDEFINED)
        method = getattr(self._api_client, method.lower())
        return method(endpoint, **request_kw)

    # ==================================================================================================================
    # SESSION     ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_session_management
    # ==================================================================================================================

    def _trusted_auth(self, *, username: str, secret: GUID, org_id: int = _utils.UNDEFINED) -> httpx.Response:
        # get the login token for a given user
        d = {"secret_key": secret, "username": username, "access_level": "FULL", "orgid": org_id}
        r = self.request("POST", "callosum/v1/tspublic/v1/session/auth/token", data=d)

        # establish a session as that user, using the token
        if r.is_success:
            d = {"auth_token": r.text, "username": username, "no_url_redirection": True}
            r = self.request("POST", "callosum/v1/tspublic/v1/session/login/token", data=d)

        return r

    def session_login(self, *, username: str, password: str, org_id: int = _utils.UNDEFINED) -> httpx.Response:
        d = {"username": username, "password": password, "rememberme": True, "orgid": org_id}
        r = self.request("POST", "callosum/v1/tspublic/v1/session/login", data=d)
        return r

    def session_logout(self) -> httpx.Response:
        r = self.request("POST", "callosum/v1/tspublic/v1/session/logout")
        return r

    def session_orgs_read(self) -> httpx.Response:
        p = {"batchsize": -1, "offset": -1}
        r = self.request("GET", "callosum/v1/tspublic/v1/session/orgs", params=p)
        return r

    def session_orgs_update(self, *, org_id: int) -> httpx.Response:
        d = {"orgid": org_id}
        r = self.request("PUT", "callosum/v1/tspublic/v1/session/orgs", data=d)
        return r

    def session_info(self) -> httpx.Response:
        r = self.request("GET", "callosum/v1/tspublic/v1/session/info")
        return r

    # ==================================================================================================================
    # ORG         ::  NOT YET SET
    # ==================================================================================================================

    def org_read(self, *, org_id: int = _utils.UNDEFINED, org_name: str = _utils.UNDEFINED) -> httpx.Response:
        p = {"id": org_id, "name": org_name, "orgScope": "ALL"}
        r = self.request("GET", "callosum/v1/tspublic/v1/org", params=p)
        return r

    def org_search(
        self,
        *,
        org_id: int = _utils.UNDEFINED,
        org_name: str = _utils.UNDEFINED,
        show_inactive: bool = False,
    ) -> httpx.Response:
        d = {"id": org_id, "name": org_name, "showinactive": show_inactive}
        r = self.request("POST", "callosum/v1/tspublic/v1/org/search", data=d)
        return r

    # ==================================================================================================================
    # USER        ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_user_management
    # ==================================================================================================================

    def user_create(
        self,
        *,
        username: str,
        display_name: str,
        password: str,
        sharing_visibility: SharingVisibility = "DEFAULT",
        user_type: str = "LOCAL_USER",
        user_properties: dict[str, Any] = _utils.UNDEFINED,
        group_guids: list[GUID] = _utils.UNDEFINED,
        # org_id: int = _utils.UNDEFINED,
    ) -> httpx.Response:
        d = {
            "name": username,
            "password": password,
            "displayname": display_name,
            "properties": user_properties,
            "groups": _utils.dumps(group_guids),
            "usertype": user_type,
            "visibility": sharing_visibility,
            "triggeredbyadmin": True,
        }
        r = self.request("POST", "callosum/v1/tspublic/v1/user", data=d)
        return r

    def user_read(self, *, user_guid: GUID = _utils.UNDEFINED, username: str = _utils.UNDEFINED) -> httpx.Response:
        p = {"userid": user_guid, "name": username}
        r = self.request("GET", "callosum/v1/tspublic/v1/user", params=p)
        return r

    def user_update(self, *, user_guid: GUID, content: UserProfile, password: str = _utils.UNDEFINED) -> httpx.Response:
        d = {"userid": user_guid, "content": json.dumps(content), "password": password, "triggeredbyadmin": True}
        r = self.request("PUT", f"callosum/v1/tspublic/v1/user/{user_guid}", data=d)
        return r

    def user_list(self) -> httpx.Response:
        r = self.request("GET", "callosum/v1/tspublic/v1/user/list")
        return r

    def user_transfer_ownership(
        self,
        *,
        from_username: str,
        to_username: str,
        object_guids: list[GUID] = _utils.UNDEFINED,
    ) -> httpx.Response:
        p = {"fromUserName": from_username, "toUserName": to_username, "objectsID": _utils.dumps(object_guids)}
        r = self.request("POST", "callosum/v1/tspublic/v1/user/transfer/ownership", params=p)
        return r

    def user_sync(
        self,
        *,
        principals: list[SecurityPrincipal],
        apply_changes: bool = False,
        remove_deleted: bool = True,
        password: str = _utils.UNDEFINED,
    ) -> httpx.Response:
        fp = pathlib.Path(tempfile.gettempdir()) / f"user-sync-{dt.datetime.now(tz=dt.timezone.UTC).timestamp()}.json"
        fp.write_text(json.dumps(principals, indent=4))

        f = {"principals": ("principals.json", fp.open("rb"), "application/json")}
        d = {"applyChanges": apply_changes, "removeDeleted": remove_deleted, "password": password}
        r = self.request("POST", "callosum/v1/tspublic/v1/user/sync", files=f, data=d)
        return r

    # ==================================================================================================================
    # GROUP       ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_groups_and_privileges
    # ==================================================================================================================

    def group_create(
        self,
        *,
        group_name: str,
        display_name: str,
        description: Optional[str] = None,
        privileges: list[GroupPrivilege],
        sharing_visibility: SharingVisibility = "DEFAULT",
        group_type: str = "LOCAL_GROUP",
    ) -> httpx.Response:
        d = {
            "name": group_name,
            "display_name": display_name,
            "description": description,
            "privileges": _utils.dumps(privileges),
            "visibility": sharing_visibility,
            "grouptype": group_type,
        }
        r = self.request("POST", "callosum/v1/tspublic/v1/group", data=d)
        return r

    def group_read(self, *, group_guid: GUID = _utils.UNDEFINED, group_name: str = _utils.UNDEFINED) -> httpx.Response:
        p = {"groupid": group_guid, "name": group_name}
        r = self.request("GET", "callosum/v1/tspublic/v1/group", params=p)
        return r

    def group_update(self, *, group_guid: GUID, content: GroupInfo) -> httpx.Response:
        d = {"groupid": group_guid, "content": json.dumps(content), "triggeredbyadmin": True}
        r = self.request("PUT", f"callosum/v1/tspublic/v1/group/{group_guid}", data=d)
        return r

    def group_list_users(self, *, group_guid: GUID) -> httpx.Response:
        r = self.request("GET", f"callosum/v1/tspublic/v1/group/{group_guid}/users")
        return r

    def group_add_user(self, *, group_guid: GUID, user_guid: GUID) -> httpx.Response:
        d = {"groupid": group_guid, "userid": user_guid}
        r = self.request("POST", f"callosum/v1/tspublic/v1/group/{group_guid}/user/{user_guid}", data=d)
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
        r = self.request("POST", "callosum/v1/tspublic/v1/searchdata", params=p)
        return r

    # ==================================================================================================================
    # METADATA    ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_metadata_management
    # ==================================================================================================================

    def metadata_assign_tag(
        self,
        *,
        metadata_guids: list[GUID],
        metadata_types: list[MetadataObjectType],
        tag_guids: list[GUID] = _utils.UNDEFINED,
        tag_names: list[str] = _utils.UNDEFINED,
    ) -> httpx.Response:
        d = {
            "id": _utils.dumps(metadata_guids),
            "type": _utils.dumps(metadata_types),
            "tagid": _utils.dumps(tag_guids),
            "tagname": _utils.dumps(tag_names),
        }
        r = self.request("POST", "callosum/v1/tspublic/v1/metadata/assigntag", data=d)
        return r

    def metadata_unassign_tag(
        self,
        *,
        metadata_guids: list[GUID],
        metadata_types: list[MetadataObjectType],
        tag_guids: list[GUID] = _utils.UNDEFINED,
        tag_names: list[str] = _utils.UNDEFINED,
    ) -> httpx.Response:
        d = {
            "id": _utils.dumps(metadata_guids),
            "type": _utils.dumps(metadata_types),
            "tagid": _utils.dumps(tag_guids),
            "tagname": _utils.dumps(tag_names),
        }
        r = self.request("POST", "callosum/v1/tspublic/v1/metadata/unassigntag", data=d)
        return r

    def metadata_list(
        self,
        *,
        metadata_type: MetadataObjectType = "QUESTION_ANSWER_BOOK",
        subtypes: list[MetadataObjectSubtype] = _utils.UNDEFINED,
        owner_types: list[MetadataObjectType] = _utils.UNDEFINED,
        category: MetadataCategory = "ALL",
        sort: SortOrder = "DEFAULT",
        sort_ascending: bool = _utils.UNDEFINED,
        offset: int = -1,
        batchsize: int = _utils.UNDEFINED,
        tag_names: list[str] = _utils.UNDEFINED,
        pattern: str = _utils.UNDEFINED,
        show_hidden: bool = False,
        skip_guids: list[GUID] = _utils.UNDEFINED,
        fetch_guids: list[GUID] = _utils.UNDEFINED,
        auto_created: bool = False,
        author_guid: GUID = _utils.UNDEFINED,
    ) -> httpx.Response:
        p = {
            "type": metadata_type,
            "subtypes": _utils.dumps(subtypes),
            "ownertypes": _utils.dumps(owner_types),
            "category": category,
            "sort": sort,
            "sortascending": sort_ascending,
            "offset": offset,
            "batchsize": batchsize,
            "tagname": _utils.dumps(tag_names),
            "pattern": pattern,
            "showhidden": show_hidden,
            "skipids": _utils.dumps(skip_guids),
            "fetchids": _utils.dumps(fetch_guids),
            "auto_created": auto_created,
            "authorguid": author_guid,
        }
        r = self.request("GET", "callosum/v1/tspublic/v1/metadata/list", params=p)
        return r

    def metadata_details(
        self,
        *,
        guids: list[GUID],
        metadata_type: MetadataObjectType = "LOGICAL_TABLE",
        show_hidden: bool = False,
    ) -> httpx.Response:
        p = {
            "type": metadata_type,
            "id": _utils.dumps(guids),
            "showhidden": show_hidden,
            "dropquestiondetails": False,
            "version": -1,
        }
        r = self.request("GET", "callosum/v1/tspublic/v1/metadata/details", params=p)
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
            "export_ids": _utils.dumps(export_guids),
            "formattype": format_type,
            "export_associated": export_associated,
            "export_fqn": export_fqn,
        }
        r = self.request("POST", "callosum/v1/tspublic/v1/metadata/tml/export", data=d)
        return r

    def metadata_tml_import(
        self,
        *,
        import_objects: list[TMLObject],
        import_policy: TMLImportPolicy = "VALIDATE_ONLY",
        force_create: bool = False,
    ) -> httpx.Response:
        d = {
            "import_objects": _utils.dumps(import_objects),
            "import_policy": import_policy,
            "force_create": force_create,
        }
        r = self.request("POST", "callosum/v1/tspublic/v1/metadata/tml/import", data=d)
        return r

    # ==================================================================================================================
    # CONNECTION  ::  https://developers.thoughtspot.com/docs/?pageid=rest-api-reference#_data_connections
    # ==================================================================================================================

    def connection_fetch_connection(
        self,
        *,
        guid: GUID,
        include_columns: bool = False,
        config: ConnectionMetadata = _utils.UNDEFINED,
        authentication_type: str = "SERVICE_ACCOUNT",
    ) -> httpx.Response:
        d = {
            "id": guid,
            "includeColumns": include_columns,
            "config": config,
            "authentication_type": authentication_type,
        }

        r = self.request("POST", "callosum/v1/tspublic/v1/connection/fetchConnection", data=d)
        return r

    def connection_fetch_live_columns(
        self,
        *,
        guid: GUID,
        tables: list[dict[str, Any]] = _utils.UNDEFINED,
        config: ConnectionMetadata = _utils.UNDEFINED,
        authentication_type: str = "SERVICE_ACCOUNT",
    ) -> httpx.Response:
        d = {
            "connection_id": guid,
            "tables": _utils.dumps(tables),
            "config": config,
            "authentication_type": authentication_type,
        }
        r = self.request("POST", "callosum/v1/connection/fetchLiveColumns", data=d)
        return r

    def connection_create(
        self,
        *,
        name: str,
        description: str,
        external_database_type: ConnectionType,
        create_empty: bool = False,
        metadata: ConnectionMetadata = _utils.UNDEFINED,
    ) -> httpx.Response:
        d = {
            "name": name,
            "description": description,
            "type": external_database_type,
            "createEmpty": create_empty,
            "metadata": metadata,
            # state  # inaccesible to the Developer
        }
        r = self.request("POST", "callosum/v1/tspublic/v1/connection/create", data=d)
        return r

    def connection_update(
        self,
        *,
        guid: GUID,
        name: str,
        description: str,
        external_database_type: ConnectionType,
        create_empty: bool = False,
        metadata: ConnectionMetadata = _utils.UNDEFINED,
    ) -> httpx.Response:
        d = {
            "name": name,
            "id": guid,
            "description": description,
            "type": external_database_type,
            "createEmpty": create_empty,
            "metadata": metadata,
            # state  # inaccesible to the Developer
        }
        r = self.request("POST", "callosum/v1/tspublic/v1/connection/update", data=d)
        return r

    def connection_export(self, *, guid: GUID) -> httpx.Response:
        p = {"id": guid}
        r = self.request("GET", "callosum/v1/tspublic/v1/connection/export", params=p)
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
        offset: int = -1,
    ) -> httpx.Response:
        d = {"type": metadata_type, "id": _utils.dumps(guids), "batchsize": batchsize, "offset": offset}
        r = self.request("POST", "callosum/v1/tspublic/v1/dependency/listdependents", data=d)
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
            "type": str(metadata_type),
            "id": _utils.dumps(guids),
            "permission": {
                "permissions": {
                    principal_guid: {"shareMode": str(access)} for principal_guid, access in permissions.items()
                },
            },
            # we don't support these options
            "emailshares": _utils.UNDEFINED,
            "notify": _utils.UNDEFINED,
            "message": _utils.UNDEFINED,
        }
        r = self.request("POST", "callosum/v1/tspublic/v1/security/share", data=d)
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
            "id": _utils.dumps(guids),
            "dependentshare": dependent_share,
            "permissiontype": permission_type,
        }
        r = self.request("GET", "callosum/v1/tspublic/v1/security/metadata/permissions", params=p)
        return r

    # ==================================================================================================================
    # THOUGHTSPOT DATASERVICE (tql, remote tsload API)
    # ==================================================================================================================

    @property
    def dataservice_url(self) -> httpx.URL:
        """Override the URL if the ThoughtSpot serving node redirects us to another."""
        if self._redirected_url_due_to_tsload_load_balancer is not None:
            url = self._redirected_url_due_to_tsload_load_balancer
        else:
            url = self._api_client._session.base_url.copy_with(port=8442)

        return url

    def dataservice_tokens_static(self) -> httpx.Response:
        r = self.request("GET", "ts_dataservice/v1/public/tql/tokens/static")
        return r

    def dataservice_tokens_dynamic(self) -> httpx.Response:
        r = self.request("GET", "ts_dataservice/v1/public/tql/tokens/dynamic")
        return r

    def dataservice_query(self, *, data: Any, timeout: float = _utils.UNDEFINED) -> httpx.Response:
        # Further reading on what can be passed to `data`
        #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_inputoutput_structure
        #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_request_body
        r = self.request("POST", "ts_dataservice/v1/public/tql/query", timeout=timeout, json=data)
        return r

    def dataservice_script(self, *, data: Any, timeout: float = _utils.UNDEFINED) -> httpx.Response:
        # Further reading on what can be passed to `data`
        #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_inputoutput_structure
        #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_request_body_2
        r = self.request("POST", "ts_dataservice/v1/public/tql/script", timeout=timeout, json=data)
        return r

    def dataservice_dataload_session(self, *, username: str, password: str) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path="/ts_dataservice/v1/public/session")
        d = {"username": username, "password": password}
        r = self.request("POST", str(fullpath), data=d)
        return r

    def dataservice_dataload_initialize(self, *, data: Any, timeout: float = _utils.UNDEFINED) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path="/ts_dataservice/v1/public/loads")
        r = self.request("POST", str(fullpath), timeout=timeout, json=data)
        return r

    def dataservice_dataload_start(
        self,
        *,
        cycle_id: GUID,
        fd: BufferedIOBase | Any,
        timeout: float = _utils.UNDEFINED,
    ) -> httpx.Response:
        # This endpoint returns immediately once the file uploads to the remote host.
        # Processing of the dataload happens concurrently, and this function may be
        # called multiple times to paralellize the full data load across multiple files.
        fullpath = self.dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}")
        r = self.request("POST", str(fullpath), timeout=timeout, files={"upload-file": fd})
        return r

    def dataservice_dataload_commit(self, *, cycle_id: GUID) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}/commit")
        r = self.request("POST", str(fullpath))
        return r

    def dataservice_dataload_status(self, *, cycle_id: GUID) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}")
        r = self.request("GET", str(fullpath))
        return r

    def dataservice_dataload_bad_records(self, *, cycle_id: GUID) -> httpx.Response:
        fullpath = self.dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}/bad_records_file")
        r = self.request("GET", str(fullpath))
        return r
