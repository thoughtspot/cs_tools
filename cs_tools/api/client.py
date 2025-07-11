from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, Optional, Union
import asyncio
import datetime as dt
import json
import logging
import pathlib

import httpx
import pydantic
import tenacity

from cs_tools import _types, utils, validators
from cs_tools.__project__ import __version__
from cs_tools.api import _retry, _transport
import cs_tools.api.utils as api_utils

log = logging.getLogger(__name__)
CALLOSUM_DEFAULT_TIMEOUT_SECONDS = 60 * 5


class RESTAPIClient(httpx.AsyncClient):
    """
    Connect to the ThoughtSpot API.

    Endpoints which fetch/search data will have successful responses cached. If you
    need to re-fetch data, you can add the CACHE_BUSTING_HEADER (x-cs-tools-cache-bust).

    INITIAL DESIGN GOALS:

      1. All endpoints should be type-hinted to take advantage of pydantic validators.

      2. Required and Default parameters should be labeled in the function signature,
         while optional parameters may be passed as keyword arguments. There may be
         slight deviation in required parameter-naming if it aids the Developer.

      3. Any V1 endpoints which need continued coverage should be prefixed with v1_.
         These endpoints may violate all other goals above as they will be progressively
         removed.
    """

    @pydantic.validate_call(validate_return=False, config=validators.METHOD_CONFIG)
    def __init__(
        self,
        base_url: Union[httpx.URL, str],
        concurrency: int = 15,
        cache_directory: Optional[pathlib.Path] = None,
        verify: bool = True,
        **client_opts: Any,
    ) -> None:
        client_opts["base_url"] = str(base_url)
        client_opts["timeout"] = CALLOSUM_DEFAULT_TIMEOUT_SECONDS
        client_opts["event_hooks"] = {"request": [self.__before_request__], "response": [self.__after_response__]}
        client_opts["headers"] = {"x-requested-by": "CS Tools", "user-agent": f"CS Tools/{__version__}"}

        client_opts["transport"] = _transport.CachedRetryTransport(
            cache_policy=_transport.CachePolicy(directory=cache_directory) if cache_directory else None,
            max_concurrent_requests=concurrency,
            retry_policy=tenacity.AsyncRetrying(
                retry=(
                    tenacity.retry_if_exception(_retry.request_errors_unless_importing_tml)
                    | tenacity.retry_if_result(_retry.if_server_is_under_pressure)
                ),
                wait=tenacity.wait_exponential(min=60, exp_base=4),
                stop=tenacity.stop_after_attempt(max_attempt_number=3),
                before_sleep=_retry.log_on_any_retry,
                reraise=True,
            ),
            verify=verify,
        )

        super().__init__(**client_opts)
        assert isinstance(self._transport, _transport.CachedRetryTransport), "Unexpected transport used for CS Tools"
        self._heartbeat_task: Optional[asyncio.Task] = None

    @property
    def cache(self) -> Optional[_transport.CachePolicy]:
        assert isinstance(self._transport, _transport.CachedRetryTransport), "Unexpected transport used for CS Tools"
        return self._transport.cache

    @property
    def max_concurrency(self) -> int:
        """Get the allowed maximum number of concurrent requests."""
        assert isinstance(self._transport, _transport.CachedRetryTransport), "Unexpected transport used for CS Tools"
        return self._transport.max_concurrency

    async def _heartbeat(self) -> None:
        """Background task to check if the connection to ThoughtSpot is still open."""
        # DEV NOTE: @boonhapus, 2023-10-18
        # JIT Authentication doesn't implement the rememberMe flag like session/login.
        #
        # rememberMe=true bypasses the default session idle timeout, setting it to a
        # much longer value of around 1 week.
        #
        # Due to caching and offline file operations, it's not gauranteed that we will
        # send the serever a request within the timeout. So instead we can perform a
        # similar operation as the ThoughtSpot UI by pinging the server every so often.
        #
        assert isinstance(self._heartbeat_task, asyncio.Task)

        while not self._heartbeat_task.done():
            try:
                await self.request("GET", "callosum/v1/session/isactive")
            except httpx.HTTPError as e:
                extra = f"data:\n{e.response.text}" if isinstance(e, httpx.HTTPStatusError) else ""
                log.debug(f"Heartbeat failed: {e} {extra}")

            await asyncio.sleep(30)

    async def __before_request__(self, request: httpx.Request) -> None:
        """
        Called after a request is fully prepared, but before it is sent to the network.

        Passed the request instance.

        Further reading:
            https://www.python-httpx.org/advanced/#event-hooks
        """
        log_msg = f">>> HTTP {request.method} -> {request.url.path}\n\t=== HEADERS ===\n{dict(request.headers)}"

        if request.url.params:
            log_msg += f"\n\t===  PARAMS ===\n{request.url.params}"

        is_sending_files_to_server = request.headers.get("Content-Type", "").startswith("multipart/form-data")

        if not is_sending_files_to_server and request.content:
            log_msg += f"\n\t===    DATA ===\n{dict(httpx.QueryParams(request.content.decode()))}"

        log.debug(f"{log_msg}\n")

    async def __after_response__(self, response: httpx.Response) -> None:
        """
        Called after the response has been fetched from the network, but before it is returned to the caller.

        Passed the response instance.

        Response event hooks are called before determining if the response body should be read or not.

        Further reading:
            https://www.python-httpx.org/advanced/#event-hooks
        """
        requested_at = response.request.headers.get("x-CS Tools-request-dispatch-time-utc", None)
        responsed_at = response.headers.get("x-CS Tools-response-receive-time-utc", None)

        if requested_at and responsed_at:
            requested_at = dt.datetime.fromisoformat(requested_at)
            responsed_at = dt.datetime.fromisoformat(responsed_at)
            elapsed = f"{(responsed_at - requested_at).total_seconds():.4f}s"
        else:
            elapsed = ""

        log_msg = f"<<< HTTP {response.status_code} <- {response.request.url.path} {elapsed}"

        if _transport.CachePolicy.CACHE_FETCHED_HEADER in response.headers:
            log_msg += " [~ cached ~]"

        if response.status_code >= 400:
            await response.aread()
            log_msg += f"\n{response.text}\n"

        log.debug(log_msg)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    async def request(self, method: str, url: Union[httpx.URL, str], **passthru: Any) -> httpx.Response:
        """Remove NULL from request data before sending/logging."""
        passthru = api_utils.scrub_undefined_sentinel(passthru, null=None)
        response = await super().request(method, url, **passthru)
        return response

    # ==================================================================================
    # AUTHENTICATION :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_authentication
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def login(
        self, username: str, password: str, org_id: Optional[int] = None, **options: Any
    ) -> Awaitable[httpx.Response]:
        """Login to ThoughtSpot."""
        options["username"] = username
        options["password"] = password
        options["org_identifier"] = org_id
        options["remember_me"] = True
        return self.post("api/rest/2.0/auth/session/login", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    async def full_access_token(
        self, username: str, token_validity: int = 300, org_id: Optional[int] = None, **options: Any
    ) -> httpx.Response:
        """Login to ThoughtSpot."""
        if options.get("password", None) is None and options.get("secret_key", None) is None:
            raise ValueError("Must provide either password or secret_key")

        options["username"] = username
        options["validity_time_in_sec"] = token_validity
        options["org_id"] = org_id

        r = await self.post("api/rest/2.0/auth/token/full", json=options)

        if r.is_success:
            self.headers["Authorization"] = f"Bearer {r.text}"

            if self._heartbeat_task is not None:
                self._heartbeat_task.cancel()

            self._heartbeat_task = asyncio.create_task(self._heartbeat(), name="THOUGHTSPOT_API_KEEPALIVE")

        return r

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    async def v1_trusted_authentication(
        self, username: _types.Name, secret_key: _types.GUID, org_id: Optional[int] = None
    ) -> httpx.Response:
        """Login to ThoughtSpot using V1 Trusted Authentication."""
        d = {"secret_key": str(secret_key), "orgid": org_id, "username": username, "access_level": "FULL"}
        r = await self.post("callosum/v1/tspublic/v1/session/auth/token", data=d)

        if r.is_success:
            d = {"auth_token": r.text, "username": username, "no_url_redirection": True}
            r = await self.post("callosum/v1/tspublic/v1/session/login/token", data=d)

            if self._heartbeat_task is not None:
                self._heartbeat_task.cancel()

            self._heartbeat_task = asyncio.create_task(self._heartbeat(), name="THOUGHTSPOT_API_KEEPALIVE")

        return r

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def logout(self) -> Awaitable[httpx.Response]:
        """Logout of ThoughtSpot."""
        if "Authorization" in self.headers:
            del self.headers["Authorization"]

        return self.post("api/rest/2.0/auth/session/logout")

    # ==================================================================================
    # SESSION :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_authentication
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def session_info(self) -> Awaitable[httpx.Response]:
        """Get the session information."""
        return self.get("api/rest/2.0/auth/session/user")

    # ==================================================================================
    # SYSTEM :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_system
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def system_info(self, **options: Any) -> Awaitable[httpx.Response]:
        """Get the system information."""
        return self.get("api/rest/2.0/system", headers=options.pop("headers", None))

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def system_config_overrides(self, **options: Any) -> Awaitable[httpx.Response]:
        """Get the system tscli overrides."""
        return self.get("api/rest/2.0/system/config-overrides", headers=options.pop("headers", None))

    # ==================================================================================
    # ORGS :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_orgs
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def orgs_search(self, **options: Any) -> Awaitable[httpx.Response]:
        """Gets a list of Orgs configured on the ThoughtSpot system."""
        return self.post("api/rest/2.0/orgs/search", headers=options.pop("headers", None), json=options)

    # ==================================================================================
    # ORGS :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_orgs
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def roles_search(self, **options: Any) -> Awaitable[httpx.Response]:
        """Gets Roles configured on a ThoughtSpot instance."""
        return self.post("api/rest/2.0/roles/search", headers=options.pop("headers", None), json=options)

    # ==================================================================================
    # LOGS :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_audit_logs
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def logs_fetch(self, utc_start: dt.datetime, utc_end: dt.datetime, **options: Any) -> Awaitable[httpx.Response]:
        """Gets security audit logs from the ThoughtSpot system."""
        assert utc_start.tzinfo == dt.timezone.utc, "'utc_start' must be an aware datetime.datetime in UTC"
        assert utc_end.tzinfo == dt.timezone.utc, "'utc_end' must be an aware datetime.datetime in UTC"
        options["log_type"] = "SECURITY_AUDIT"
        options["start_epoch_time_in_millis"] = int(utc_start.timestamp() * 1000)
        options["end_epoch_time_in_millis"] = int(utc_end.timestamp() * 1000)
        options["get_all_logs"] = True
        return self.post("api/rest/2.0/logs/fetch", json=options)

    # ==================================================================================
    # METADATA :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_metadata
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def metadata_search(self, guid: _types.ObjectIdentifier, **options: Any) -> Awaitable[httpx.Response]:
        """Get a list of ThoughtSpot objects."""
        if "metadata" not in options:
            options["metadata"] = [{"identifier": guid}]

        options["include_headers"] = True
        return self.post("api/rest/2.0/metadata/search", headers=options.pop("headers", None), json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def metadata_delete(self, guid: _types.ObjectIdentifier, **options: Any) -> Awaitable[httpx.Response]:
        """Removes the specified metadata object from the ThoughtSpot system."""
        if "metadata" not in options:
            options["metadata"] = [{"identifier": guid}]

        return self.post("api/rest/2.0/metadata/delete", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def metadata_tml_export(
        self, guid: _types.ObjectIdentifier, export_fqn: bool = True, **options: Any
    ) -> Awaitable[httpx.Response]:
        """Get the EDOC of the ThoughtSpot object."""
        options["metadata"] = [{"identifier": guid}]
        options["export_fqn"] = export_fqn
        return self.post("api/rest/2.0/metadata/tml/export", headers=options.pop("headers", None), json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def metadata_tml_import(
        self, tmls: list[str], policy: _types.TMLImportPolicy, **options: Any
    ) -> Awaitable[httpx.Response]:
        """Push the EDOC of the object into ThoughtSpot."""
        options["metadata_tmls"] = tmls
        options["import_policy"] = policy
        return self.post("api/rest/2.0/metadata/tml/import", headers=options.pop("headers", None), json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def metadata_tml_async_import(
        self, tmls: list[str], policy: _types.TMLImportPolicy, **options: Any
    ) -> Awaitable[httpx.Response]:
        """Schedules a task to import TML files into ThoughtSpot."""
        options["metadata_tmls"] = tmls
        options["import_policy"] = policy
        return self.post("api/rest/2.0/metadata/tml/async/import", headers=options.pop("headers", None), json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def metadata_tml_async_status(
        self, include_import_response: bool = True, **options: Any
    ) -> Awaitable[httpx.Response]:
        """Schedules a task to import TML files into ThoughtSpot."""
        options["include_import_response"] = include_import_response
        return self.post("api/rest/2.0/metadata/tml/async/status", headers=options.pop("headers", None), json=options)

    # ==================================================================================
    # CONNECTIONS :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_connections
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def connection_search(self, guid: _types.ObjectIdentifier, **options: Any) -> Awaitable[httpx.Response]:
        """Get a Connection and its Table objects."""
        options["connections"] = [{"identifier": guid}]
        options["include_details"] = True
        return self.post("api/rest/2.0/connection/search", json=options)

    # ==================================================================================
    # USERS :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_users
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def users_search(
        self,
        guid: Optional[_types.ObjectIdentifier] = None,
        record_offset: int = 0,
        record_size: int = 10,
        **options: Any,
    ) -> Awaitable[httpx.Response]:
        """Get a list of ThoughtSpot users."""
        if guid is not None:
            options["user_identifier"] = guid

        options["record_offset"] = record_offset
        options["record_size"] = record_size

        headers = options.pop("headers", None)
        timeout = options.pop("timeout", httpx.USE_CLIENT_DEFAULT)
        return self.post("api/rest/2.0/users/search", headers=headers, timeout=timeout, json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def users_create(self, **options: Any) -> Awaitable[httpx.Response]:
        """Create a ThoughtSpot user."""
        return self.post("api/rest/2.0/users/create", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def users_update(self, user_identifier: _types.ObjectIdentifier, **options: Any) -> Awaitable[httpx.Response]:
        """Updates a ThoughtSpot user."""
        return self.post(f"api/rest/2.0/users/{user_identifier}/update", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def users_delete(self, user_identifier: _types.ObjectIdentifier, **options: Any) -> Awaitable[httpx.Response]:
        """Deletes a ThoughtSpot user."""
        return self.post(f"api/rest/2.0/users/{user_identifier}/delete", json=options)

    # ==================================================================================
    # GROUPS :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_groups
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def groups_search(
        self,
        guid: Optional[_types.ObjectIdentifier] = None,
        record_offset: int = 0,
        record_size: int = 10,
        **options: Any,
    ) -> Awaitable[httpx.Response]:
        """Get a list of ThoughtSpot groups."""
        if guid is not None:
            options["group_identifier"] = guid

        options["record_offset"] = record_offset
        options["record_size"] = record_size

        headers = options.pop("headers", None)
        timeout = options.pop("timeout", httpx.USE_CLIENT_DEFAULT)
        return self.post("api/rest/2.0/groups/search", headers=headers, timeout=timeout, json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def groups_search_v1(self, **options: Any) -> Awaitable[httpx.Response]:  # noqa: ARG002
        """Get a list of ThoughtSpot groups with v1 endpoint."""
        return self.get("callosum/v1/tspublic/v1/group")

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def group_list_users(self, group_guid: _types.ObjectIdentifier, **options: Any) -> Awaitable[httpx.Response]:  # noqa: ARG002
        """Get a list of ThoughtSpot users in a group with v1 endpoint."""
        r = self.get(f"callosum/v1/tspublic/v1/group/{group_guid}/users")
        return r

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def groups_create(self, **options: Any) -> Awaitable[httpx.Response]:
        """Create a ThoughtSpot group."""
        return self.post("api/rest/2.0/groups/create", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def groups_update(self, group_identifier: _types.ObjectIdentifier, **options: Any) -> Awaitable[httpx.Response]:
        """Updates a ThoughtSpot group."""
        return self.post(f"api/rest/2.0/groups/{group_identifier}/update", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def groups_delete(self, group_identifier: _types.ObjectIdentifier) -> Awaitable[httpx.Response]:
        """Deletes a ThoughtSpot group."""
        return self.post(f"api/rest/2.0/groups/{group_identifier}/delete")

    # ==================================================================================
    # TAGS :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_tags
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def tags_search(self, **options: Any) -> Awaitable[httpx.Response]:
        """Gets a list of tag objects available on the ThoughtSpot system."""
        return self.post("api/rest/2.0/tags/search", headers=options.pop("headers", None), json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def tags_create(self, name: _types.Name, **options: Any) -> Awaitable[httpx.Response]:
        """Creates a tag object."""
        options["name"] = name
        return self.post("api/rest/2.0/tags/create", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def tags_delete(self, tag_identifier: _types.ObjectIdentifier, **options: Any) -> Awaitable[httpx.Response]:
        """Creates a tag object."""
        return self.post(f"api/rest/2.0/tags/{tag_identifier}/delete", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def tags_assign(
        self, guid: _types.ObjectIdentifier, tag: _types.ObjectIdentifier, **options: Any
    ) -> Awaitable[httpx.Response]:
        """Assigns tags to Liveboards, Answers, Tables, and Worksheets."""
        if "metadata" not in options:
            options["metadata"] = [{"identifier": guid}]

        options["tag_identifiers"] = [tag]
        return self.post("api/rest/2.0/tags/assign", json=options)

    # ==================================================================================
    # SCHEDULES :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_schedules
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def schedules_search(self, liveboard_guid: _types.ObjectIdentifier, **options: Any) -> Awaitable[httpx.Response]:
        """Get a list of Liveboard schedules."""
        options["metadata"] = [{"identifier": str(liveboard_guid)}]
        return self.post("api/rest/2.0/schedules/search", headers=options.pop("headers", None), json=options)

    # ==================================================================================
    # DATA :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_data
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def search_data(
        self, logical_table_identifier: _types.ObjectIdentifier, query_string: str, **options: Any
    ) -> Awaitable[httpx.Response]:
        """Generates an Answer from a given data source."""
        options["query_string"] = query_string
        options["logical_table_identifier"] = str(logical_table_identifier)
        return self.post("api/rest/2.0/searchdata", json=options)

    # ==================================================================================
    # SECURITY :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_security
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def security_metadata_assign(
        self, guid: _types.ObjectIdentifier, user_identifier: _types.PrincipalIdentifier, **options: Any
    ) -> Awaitable[httpx.Response]:
        """Transfers the ownership of one or several objects from one user to another."""
        if "metadata" not in options:
            options["metadata"] = [{"identifier": guid}]

        options["user_identifier"] = user_identifier
        return self.post("api/rest/2.0/security/metadata/assign", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def security_metadata_permissions(
        self, guid: _types.ObjectIdentifier, permission_type: _types.ShareType = "DEFINED", **options: Any
    ) -> Awaitable[httpx.Response]:
        """Get a list of Users and Groups who can access the ThoughtSpot object."""
        if "metadata" not in options:
            options["metadata"] = [{"identifier": guid}]

        options["permission_type"] = permission_type

        headers = options.pop("headers", None)
        timeout = options.pop("timeout", httpx.USE_CLIENT_DEFAULT)
        return self.post(
            "api/rest/2.0/security/metadata/fetch-permissions", headers=headers, timeout=timeout, json=options
        )

    # @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    # @_transport.CachePolicy.mark_cacheable
    async def v1_security_metadata_permissions(
        self,
        guid: _types.ObjectIdentifier,
        api_object_type: _types.APIObjectType,
        permission_type: _types.ShareType = "DEFINED",
        **options: Any,
    ) -> httpx.Response:
        """Get a list of Users and Groups who can access the ThoughtSpot object."""
        # TODO: REMOVE THIS WHOLE METHOD AFTER 10.3.0.sw IS n-2 PER OUR SUPPORT POLICY.
        V2_TO_V1_TYPES = {
            "CONNECTION": "DATA_SOURCE",
            "LOGICAL_TABLE": "LOGICAL_TABLE",
            "LIVEBOARD": "PINBOARD_ANSWER_BOOK",
            "ANSWER": "QUESTION_ANSWER_BOOK",
            "LOGICAL_COLUMN": "LOGICAL_COLUMN",
        }

        headers = options.pop("headers", None)
        options["type"] = V2_TO_V1_TYPES.get(api_object_type)
        options["permissiontype"] = permission_type

        if "id" not in options:
            options["id"] = [guid]

        # DEV NOTE: @boonhapus, 2024/12/09
        # TEHCNICALLY 👆 THIS SHOULD BE ALL WE NEED IN MOST CASES.. BUT WHEN THE
        # REQUEST URL IS TOO LARGE, WE GOTTA TAKE SPECIAL CARE.

        # THIS CAN BE UGLY SINCE WE'RE REMOVING IT AFTER 10.3 ANYWAY.
        # HANDLE 414 Request-URI Too Large
        tasks: list[asyncio.Task] = []

        async with utils.BoundedTaskGroup(max_concurrent=max(self.max_concurrency - 1, 1)) as g:
            # LET'S NOT BE RIDICULOUS, KEEP n TO A LOWISH NUMBER SO WE DON'T OVERLOAD THE SYSTEM.
            for idx, batch in enumerate(utils.batched(options["id"], n=25)):
                assert all(isinstance(x, str) for x in batch), "expected all ids to be strings"
                options["id"] = json.dumps(list(batch))
                c = self.get("callosum/v1/tspublic/v1/security/metadata/permissions", headers=headers, params=options)
                t = g.create_task(c, name=f"v1/security/metadata/permissions REQUEST #{idx + 1}")
                tasks.append(t)

        data: _types.APIResult = {}

        for task in tasks:
            try:
                r = await task
                r.raise_for_status()
            # IF ANY ONE TASK ERRORS, KICK IT BACK IMMEDIATELY.
            except httpx.HTTPStatusError as e:
                return e.response
            else:
                data.update(r.json())

        # BUILD A NEW RESPONSE WITH THE COMBINED OUTPUT FROM ALL THE OTHER RESPONSES.
        r = httpx.Response(
            status_code=200,
            headers=headers,
            json=data,
            extensions=r.extensions,
            request=r.request,
        )

        return r

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def security_metadata_share(
        self,
        guids: list[_types.GUID],
        principals: list[_types.PrincipalIdentifier],
        share_mode: _types.ShareMode = "NO_ACCESS",
        notify_on_share: bool = False,
        **options: Any,
    ) -> Awaitable[httpx.Response]:
        """Allows sharing metadata objects with users and groups in ThoughtSpot."""
        if "metadata" not in options:
            options["metadata"] = [{"identifier": _} for _ in guids]

        options["permissions"] = [
            {
                "principal": {"identifier": principal},
                "share_mode": share_mode,
            }
            for principal in principals
        ]

        options["notify_on_share"] = notify_on_share
        options["message"] = options.get("message", "")

        return self.post("api/rest/2.0/security/metadata/share", json=options)

    # ==================================================================================
    # VERSION CONTROL :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_version_control
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    @_transport.CachePolicy.mark_cacheable
    def vcs_git_config_search(self, **options: Any) -> Awaitable[httpx.Response]:
        """Gets Git repository connections configured on the ThoughtSpot instance."""
        return self.post("api/rest/2.0/vcs/git/config/search", headers=options.pop("headers", None), json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def vcs_git_config_create(
        self,
        repository_url: str,
        username: str,
        access_token: str,
        **options: Any,
    ) -> Awaitable[httpx.Response]:
        """Allows you to connect a ThoughtSpot instance to a Git repository."""
        options["repository_url"] = repository_url
        options["username"] = username
        options["access_token"] = access_token
        return self.post("api/rest/2.0/vcs/git/config/create", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def vcs_git_branches_commit(
        self,
        guids: list[_types.GUID],
        commit_message: str,
        delete_aware: bool = True,
        **options: Any,
    ) -> Awaitable[httpx.Response]:
        """Allows you to connect a ThoughtSpot instance to a Git repository."""
        if "metadata" not in options:
            options["metadata"] = [{"identifier": _} for _ in guids]

        options["delete_aware"] = delete_aware
        options["comment"] = commit_message
        return self.post("api/rest/2.0/vcs/git/branches/commit", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def vcs_git_branches_validate(
        self,
        source_branch_name: str,
        target_branch_name: str,
        **options: Any,
    ) -> Awaitable[httpx.Response]:
        """Allows you to connect a ThoughtSpot instance to a Git repository."""
        options["source_branch_name"] = source_branch_name
        options["target_branch_name"] = target_branch_name
        return self.post("api/rest/2.0/vcs/git/branches/validate", json=options)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def vcs_git_commits_deploy(self, branch_name: str, **options: Any) -> Awaitable[httpx.Response]:
        """Allows you to deploy a commit and publish TML content to your ThoughtSpot instance."""
        options["branch_name"] = branch_name
        return self.post("api/rest/2.0/vcs/git/commits/deploy", json=options)

    # ==================================================================================
    # REMOTE TQL :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_security
    # ==================================================================================

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def v1_dataservice_query(self, **options: Any) -> Awaitable[httpx.Response]:
        """Allows you to query the ThoughtSpot TQL cli from a remote machine."""
        # Further reading on what can be passed to `data`
        #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_inputoutput_structure
        #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_request_body
        timeout = options.pop("timeout", httpx.USE_CLIENT_DEFAULT)

        return self.post("ts_dataservice/v1/public/tql/query", timeout=timeout, json=options)

    # ==================================================================================
    # REMOTE TSLOAD :: https://developers.thoughtspot.com/docs/rest-apiv2-reference#_security
    # ==================================================================================

    @property
    def v1_dataservice_url(self) -> httpx.URL:
        """Override the URL if the ThoughtSpot serving node redirects us to another."""
        if hasattr(self, "_redirected_url_due_to_tsload_load_balancer"):
            url = self._redirected_url_due_to_tsload_load_balancer
        else:
            url = self.base_url.copy_with(port=8442)

        return url

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def v1_dataservice_dataload_session(self, username: str, password: str) -> Awaitable[httpx.Response]:
        """Use this API to authenticate and sign in a user."""
        # Further reading:
        #   https://docs.thoughtspot.com/software/latest/tsload-api#login
        fullpath = self.v1_dataservice_url.copy_with(path="/ts_dataservice/v1/public/session")

        return self.post(str(fullpath), json={"username": username, "password": password})

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def v1_dataservice_dataload_initialize(
        self, *, data: Any, timeout: Optional[float] = None
    ) -> Awaitable[httpx.Response]:
        """Initialize the data load operation."""
        # Further reading on what can be passed to `data`
        #   https://docs.thoughtspot.com/software/latest/tsload-api#start-load
        fullpath = self.v1_dataservice_url.copy_with(path="/ts_dataservice/v1/public/loads")

        return self.post(str(fullpath), timeout=timeout, json=data)

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def v1_dataservice_dataload_start(
        self,
        *,
        cycle_id: _types.GUID,
        fd: Any,
        **options: Any,
    ) -> Awaitable[httpx.Response]:
        """Load a chunk of data to Falcon."""
        # Further reading:
        #   https://docs.thoughtspot.com/software/latest/tsload-api#load
        fullpath = self.v1_dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}")

        # DEV NOTE: @boonhapus
        # This endpoint returns immediately once the file uploads to the remote host.
        # Processing of the dataload happens concurrently, and this function may be
        # called multiple times to paralellize the full data load across multiple files.
        timeout = options.pop("timeout", httpx.USE_CLIENT_DEFAULT)

        return self.post(str(fullpath), timeout=timeout, files={"upload-file": fd})

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def v1_dataservice_dataload_commit(self, *, cycle_id: _types.GUID) -> Awaitable[httpx.Response]:
        """Commit the data load to Falcon."""
        # Further reading:
        #   https://docs.thoughtspot.com/software/latest/tsload-api#commit-load
        fullpath = self.v1_dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}/commit")

        return self.post(str(fullpath))

    @pydantic.validate_call(validate_return=True, config=validators.METHOD_CONFIG)
    def v1_dataservice_dataload_status(self, *, cycle_id: _types.GUID) -> Awaitable[httpx.Response]:
        """Get the current status of a data load."""
        # Further reading:
        #   https://docs.thoughtspot.com/software/latest/tsload-api#_status_of_load
        fullpath = self.v1_dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}")

        return self.get(str(fullpath))

    def v1_dataservice_dataload_bad_records(self, *, cycle_id: _types.GUID) -> Awaitable[httpx.Response]:
        """View the bad records file data."""
        # Further reading:
        #   https://docs.thoughtspot.com/software/latest/tsload-api#_status_of_load
        # fmt: off
        fullpath = self.v1_dataservice_url.copy_with(path=f"/ts_dataservice/v1/public/loads/{cycle_id}/bad_records_file")  # noqa: E501
        # fmt: on

        return self.get(str(fullpath))
