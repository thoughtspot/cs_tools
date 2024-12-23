from __future__ import annotations

from collections.abc import Awaitable
import asyncio
import logging

import httpx

from cs_tools import errors, types, utils
from cs_tools.api.client import RESTAPIClient
from cs_tools.datastructures import LocalSystemInfo, SessionContext
from cs_tools.settings import CSToolsConfig

log = logging.getLogger(__name__)


class ThoughtSpot:
    """
    The top-level ThoughtSpot object.

    Represents a connection to your ThoughtSpot cluster.
    """

    def __init__(self, config: CSToolsConfig, auto_login: bool = False):
        self._event_loop = utils.get_event_loop()
        self._session_context: SessionContext | None = None
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

    def login(self) -> None:
        """Log in to ThoughtSpot."""
        # RESET SESSION_CONTEXT IN CASE WE ATTEMPT TO CALL .login MULTIPLE TIMES
        self._session_context = None

        username = self.config.thoughtspot.username
        org_id = self.config.thoughtspot.default_org

        attempted: dict[str, httpx.Response] = {}
        active_session = False
        __auth_ctx__ = "NONE"

        #
        # AUTHENTICATE
        #
        try:
            c: Awaitable[httpx.Response]  # Coroutine from RESTAPIClient

            if not active_session and (bearer_token := self.config.thoughtspot.bearer_token) is not None:
                self.api.headers["Authorization"] = f"Bearer {bearer_token}"
                c = self.api.request("GET", "callosum/v1/session/isActive")
                r = utils.run_sync(c)

                attempted["Bearer Token"] = r

                if active_session := r.is_success:
                    __auth_ctx__ = "BEARER_TOKEN"
                else:
                    self.api.headers.pop("Authorization")

            if not active_session and (secret_key := self.config.thoughtspot.secret_key) is not None:
                c = self.api.v1_trusted_authentication(username=username, secret_key=secret_key, org_id=org_id)
                r = utils.run_sync(c)

                attempted["V1 Trusted"] = r

                if active_session := r.is_success:
                    __auth_ctx__ = "TRUSTED_AUTH"

            if not active_session and self.config.thoughtspot.password is not None:
                c = self.api.login(username=username, password=self.config.thoughtspot.decoded_password, org_id=org_id)
                r = utils.run_sync(c)

                attempted["Basic"] = r

                if active_session := r.is_success:
                    __auth_ctx__ = "BASIC"

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

            raise errors.ThoughtSpotUnreachable(reason=reason, mitigation=fixing) from None

        # PROCESS THE RESPONSE TO DETERMINE IF THE CLUSTER IS IN STANDBY
        if "Site Maintenance" in r.text:
            reason = "Cluster is in Maintenance Mode."
            fixing = f"Visit [fg-secondary]{self.config.thoughtspot.url}[/] to confirm or contact your Administrator."
            raise errors.ThoughtSpotUnreachable(reason=reason, mitigation=fixing) from None

        #
        # PROCESS RESPONSE
        #
        for method, _ in attempted.items():
            if not _.is_success:
                log.info(f"Attempted {method} Authentication (HTTP {r.status_code}), see logs for details..")

        if any(not _.is_success for _ in attempted.values()):
            raise errors.AuthenticationFailed(ts_config=self.config, desired_org_id=org_id) from None

        # GOOD TO GO , INTERACT WITH THE APIs
        c = self.api.session_info()
        r = utils.run_sync(c)
        __session_info__ = r.json()

        c = self.api.system_info()
        r = utils.run_sync(c)
        __system_info__ = r.json() if r.is_success else {}  # REQUIRES: ADMINISTARTION | SYSTEM_INFO_ADMINISTRATION

        c = self.api.system_config_overrides()
        r = utils.run_sync(c)
        __overrides_info__ = r.json() if r.is_success else {}  # REQUIRES: ADMINISTARTION | APPLICATION_ADMINISTRATION

        d = {
            "__url__": self.config.thoughtspot.url,
            "__system_info__": __system_info__,
            "__overrides_info__": __overrides_info__,
            "__session_info__": __session_info__,
            "__is_orgs_enabled__": utils.run_sync(self.api.get("callosum/v1/tspublic/v1/session/orgs")).is_success,
            "__auth_context__": __auth_ctx__,
            **r.json(),
        }
        self._session_context = ctx = SessionContext(thoughtspot=d, user=d)

        log.debug(f"SESSION CONTEXT\n{ctx.model_dump_json(indent=4)}")

    def logout(self) -> None:
        """Log out of ThoughtSpot."""
        utils.run_sync(self.api.logout())


if __name__ == "__main__":
    from cs_tools import thoughtspot
    from cs_tools.settings import CSToolsConfig

    logging.basicConfig(level=logging.INFO)

    cfg = CSToolsConfig.from_name(name="champagne")
    ts = thoughtspot.ThoughtSpot(config=cfg)
    ts.login()
