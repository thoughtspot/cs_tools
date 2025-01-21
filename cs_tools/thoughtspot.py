from __future__ import annotations

from collections.abc import Awaitable
from typing import Optional
import asyncio
import json
import logging

import httpx

from cs_tools import _types, errors, utils
from cs_tools.api.client import RESTAPIClient
from cs_tools.datastructures import LocalSystemInfo, SessionContext
from cs_tools.settings import CSToolsConfig

_LOG = logging.getLogger(__name__)


class ThoughtSpot:
    """
    The top-level ThoughtSpot object.

    Represents a connection to your ThoughtSpot cluster.
    """

    def __init__(self, config: CSToolsConfig, auto_login: bool = False):
        self._event_loop = utils.get_event_loop()
        self._session_context: Optional[SessionContext] = None
        self.config = config
        self.api = RESTAPIClient(
            base_url=str(config.thoughtspot.url),
            concurrency=15,
            # cache_directory=config.temp_dir,
            verify=not config.thoughtspot.disable_ssl,
            proxy=config.thoughtspot.proxy,
        )

        if auto_login:
            self.login()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """Fetch the underlying event loop."""
        return self._event_loop

    @property
    def session_context(self) -> SessionContext:
        """Returns information about the ThoughtSpot session."""
        if self._session_context is None:
            raise errors.NoSessionEstablished("SessionContext has not been established.")

        return self._session_context

    def _attempt_build_context(
        self, auth_type: _types.AuthContext, desired_org_id: Optional[int] = None
    ) -> _types.AuthContext:
        c = self.api.session_info()
        r = utils.run_sync(c)

        if _IS_SESSION_ERROR := httpx.codes.is_client_error(r.status_code):
            return "NONE"

        # GOOD TO GO , INTERACT WITH THE APIs
        __session_info__ = r.json()

        c = self.api.system_info()
        r = utils.run_sync(c)
        __system_info__ = r.json() if r.is_success else {}  # REQUIRES: ADMINISTARTION | SYSTEM_INFO_ADMINISTRATION

        c = self.api.system_config_overrides()
        r = utils.run_sync(c)
        __overrides_info__ = r.json() if r.is_success else {}  # REQUIRES: ADMINISTARTION | APPLICATION_ADMINISTRATION

        if not __system_info__:
            _LOG.warning("CS Tools is meant to be run from an Administrator level context.")
            __system_info__ = {
                "id": "UNKNOWN",
                "release_version": "v0.0.0",
                "time_zone": "UNKNOWN",
                "type": "UNKNOWN",
            }

        d = {
            "__url__": self.config.thoughtspot.url,
            "__system_info__": __system_info__,
            "__overrides_info__": __overrides_info__,
            "__session_info__": __session_info__,
            "__is_orgs_enabled__": utils.run_sync(self.api.get("callosum/v1/tspublic/v1/session/orgs")).is_success,
            "__auth_context__": auth_type,
        }

        self._session_context = ctx = SessionContext(thoughtspot=d, user=d)

        if _NOT_IN_DESIRED_ORG := (desired_org_id is not None and ctx.user.org_context != desired_org_id):
            # DEV NOTE: @boonhapus, 2025/01/21
            #
            # SCAL-239189 ... FALL BACK TO V1 SWITCH ORGS API
            #
            if ctx.thoughtspot.is_iam_v2_enabled:
                c = self.api.put("callosum/v1/tspublic/v1/session/orgs", data={"orgid": desired_org_id})
                _ = utils.run_sync(c)

                if _.is_success:
                    return self._attempt_build_context(auth_type=auth_type, desired_org_id=desired_org_id)
            # == /
            return "NONE"

        return ctx.user.auth_context

    def login(self, org_id: Optional[int] = None) -> None:
        """Log in to ThoughtSpot."""
        # RESET SESSION_CONTEXT IN CASE WE ATTEMPT TO CALL .login MULTIPLE TIMES
        self._session_context = None

        username = self.config.thoughtspot.username
        org_id = self.config.thoughtspot.default_org if org_id is None else org_id

        attempted: dict[str, httpx.Response] = {}
        __auth_ctx__: _types.AuthContext = "NONE"

        #
        # AUTHENTICATE
        #
        try:
            c: Awaitable[httpx.Response]  # Coroutine from RESTAPIClient

            if __auth_ctx__ == "NONE" and (bearer_token := self.config.thoughtspot.bearer_token) is not None:
                self.api.headers["Authorization"] = f"Bearer {bearer_token}"
                c = self.api.request("GET", "api/rest/2.0/auth/session/token")
                r = utils.run_sync(c)

                assert "Site Maintenance" not in r.text, "Cluster is in Maintenance Mode."

                attempted["Bearer Token"] = r

                __auth_ctx__ = self._attempt_build_context(auth_type="BEARER_TOKEN", desired_org_id=org_id)

                if __auth_ctx__ == "NONE":
                    self.api.headers.pop("Authorization")

                    # WE'LL FAKE THE STATUS CODE TO GIVE MORE INFO IN THE ERROR.
                    r.status_code = httpx.codes.BAD_REQUEST
                    r._content = json.dumps({"cs_tools": {"invalid_for_org_id": org_id}, "og_resp": r.text}).encode()

            if __auth_ctx__ == "NONE" and (secret_key := self.config.thoughtspot.secret_key) is not None:
                c = self.api.v1_trusted_authentication(username=username, secret_key=secret_key, org_id=org_id)
                r = utils.run_sync(c)

                assert "Site Maintenance" not in r.text, "Cluster is in Maintenance Mode."

                attempted["V1 Trusted"] = r

                __auth_ctx__ = self._attempt_build_context(auth_type="TRUSTED_AUTH", desired_org_id=org_id)

                if __auth_ctx__ == "NONE":
                    # WE'LL FAKE THE STATUS CODE TO GIVE MORE INFO IN THE ERROR.
                    r.status_code = httpx.codes.BAD_REQUEST
                    r._content = json.dumps({"cs_tools": {"invalid_for_org_id": org_id}, "og_resp": r.text}).encode()

            if __auth_ctx__ == "NONE" and self.config.thoughtspot.password is not None:
                c = self.api.login(username=username, password=self.config.thoughtspot.decoded_password, org_id=org_id)
                r = utils.run_sync(c)

                assert "Site Maintenance" not in r.text, "Cluster is in Maintenance Mode."

                attempted["Basic"] = r

                __auth_ctx__ = self._attempt_build_context(auth_type="BASIC", desired_org_id=org_id)

                if __auth_ctx__ == "NONE":
                    # WE'LL FAKE THE STATUS CODE TO GIVE MORE INFO IN THE ERROR.
                    r.status_code = httpx.codes.BAD_REQUEST
                    r._content = json.dumps({"cs_tools": {"invalid_for_org_id": org_id}, "og_resp": r.text}).encode()

        # REQUEST ERRORS DENOTE CONNECTIVITY ISSUES TO THE CLUSTER
        except httpx.RequestError as e:
            cannot_verify_local_ssl_cert = "SSL: CERTIFICATE_VERIFY_FAILED" in str(e)

            if cannot_verify_local_ssl_cert and LocalSystemInfo().is_mac_osx:
                reason = "Outdated Python default certificate detected."
                fixing = "Double click the bundled certificates at [fg-secondary]/Applications/Python x.y/Install Certificates.command"  # noqa: E501

            elif cannot_verify_local_ssl_cert and LocalSystemInfo().is_windows:
                reason = "Outdated Python default certificate detected."
                fixing = f"Try running [fg-secondary]cs_tools config modify --config {self.config.name} --disable-ssl"

            else:
                reason = f"Cannot connect to ThoughtSpot ([fg-secondary]{self.config.thoughtspot.url}[/])"
                fixing = f"Does your ThoughtSpot require a VPN to connect?\n\n[white]>>>[/] {e}"

            _LOG.debug(f"Raw error: {e}", exc_info=True)
            raise errors.ThoughtSpotUnreachable(reason=reason, fixing=fixing) from None

        # PROCESS THE RESPONSE TO DETERMINE WHY THE CLUSTER IS IN STANDBY
        except AssertionError:
            reason = "Cluster is in Maintenance Mode."
            fixing = f"Visit [fg-secondary]{self.config.thoughtspot.url}[/] to confirm or contact your Administrator."
            raise errors.ThoughtSpotUnreachable(reason=reason, fixing=fixing) from None

        #
        # PROCESS RESPONSE
        #
        for meth, _ in attempted.items():
            if not _.is_success:
                _LOG.info(f"Attempted {meth} Authentication and failed (HTTP {_.status_code}), see logs for details..")
                _LOG.debug(r.text)

        if all(not _.is_success for _ in attempted.values()):
            raise errors.AuthenticationFailed(ts_config=self.config, ctx=__auth_ctx__, desired_org_id=org_id) from None

        _LOG.debug(f"SESSION CONTEXT\n{self.session_context.model_dump_json(indent=4)}")

    def switch_org(self, org_id: _types.OrgIdentifier) -> _types.APIResult:
        """Establish a new session in the target Org."""
        c = self.api.orgs_search()
        r = utils.run_sync(c)

        try:
            r.raise_for_status()
            _ = next(iter(r.json()))
        except StopIteration:
            raise errors.CSToolsError(f"Could not find the org '{org_id}'") from None

        if _["id"] != self.session_context.user.org_context:
            # DEV NOTE: @boonhapus, 2025/01/11
            # This is exactly how ThoughtSpot performs the org/switch operation..
            # instead, establish a new session in the target org.
            self.login(org_id=_["id"])

        return _

    def logout(self) -> None:
        """Log out of ThoughtSpot."""
        utils.run_sync(self.api.logout())
