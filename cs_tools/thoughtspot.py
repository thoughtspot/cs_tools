from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import collections
import logging

import httpx

from cs_tools import errors
from cs_tools.api._client import RESTAPIClient
from cs_tools.api.middlewares import (
    AnswerMiddleware,
    GroupMiddleware,
    LogicalTableMiddleware,
    MetadataMiddleware,
    OrgMiddleware,
    PinboardMiddleware,
    SearchMiddleware,
    TagMiddleware,
    TMLMiddleware,
    TQLMiddleware,
    TSLoadMiddleware,
    UserMiddleware,
)
from cs_tools.datastructures import SessionContext
from cs_tools.errors import AuthenticationError, ThoughtSpotUnavailable

if TYPE_CHECKING:
    from cs_tools.settings import CSToolsConfig

log = logging.getLogger(__name__)


class ThoughtSpot:
    """
    The top-level ThoughtSpot object.

    Represents a connection to your ThoughtSpot cluster.
    """

    def __init__(self, config: CSToolsConfig, auto_login: bool = False):
        self.config = config
        self.api = RESTAPIClient(ts_url=str(config.thoughtspot.url), verify=config.thoughtspot.disable_ssl)
        self._session_context: Optional[SessionContext] = None

        # ==============================================================================================================
        # API MIDDLEWARES: logically grouped API interactions within ThoughtSpot
        # ==============================================================================================================
        self.org = OrgMiddleware(self)
        self.search = SearchMiddleware(self)
        self.user = UserMiddleware(self)
        self.group = GroupMiddleware(self)
        # self.tml
        self.metadata = MetadataMiddleware(self)
        self.pinboard = self.liveboard = PinboardMiddleware(self)
        self.answer = AnswerMiddleware(self)
        # self.connection
        self.logical_table = LogicalTableMiddleware(self)
        self.tag = TagMiddleware(self)
        self.tml = TMLMiddleware(self)
        self.tql = TQLMiddleware(self)
        self.tsload = TSLoadMiddleware(self)

        if auto_login:
            self.login()

    @property
    def session_context(self) -> SessionContext:
        """Returns information about the ThoughtSpot session."""
        if self._session_context is None:
            raise errors.NoSessionEstablished()

        return self._session_context

    def _attempt_do_authenticate(self, authentication_method, **authentication_keywords) -> httpx.Response:
        """
        Peform the authentication loop, with REQUEST and RESPONSE error handling.

        If authentication is successful, the .session_context will be set.
        """
        try:
            r = authentication_method(**authentication_keywords)
            r.raise_for_status()

        # REQUEST ERROR, COULD NOT REACH THOUGHTSPOT
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            if "SSL: CERTIFICATE_VERIFY_FAILED" in str(e):
                reason = "Outdated Python default certificate detected."
                mitigation = (
                    f"Quick fix: run [b blue]cs_tools config modify --config {self.config.name} --disable_ssl[/] "
                    f"and try again.\n\nLonger fix: try running [b blue]cs_tools self pip install certifi "
                    f"--upgrade[/] and try again."
                )
            else:
                reason = (
                    f"Cannot connect to ThoughtSpot ( [b blue]{self.config.thoughtspot.url}[/] ) from your " f"computer"
                )
                mitigation = f"Does your ThoughtSpot require a VPN to connect?\n\n[white]>>>[/] {e}"

            raise errors.ThoughtSpotUnreachable(reason=reason, mitigation=mitigation) from None

        # RESPONSE ERROR, UNAUTHORIZED OR SERVER ERROR
        # - RETURN THE RESPONSE SO THAT IT CAN BE PROCESSED BY THE CALLER
        except httpx.HTTPStatusError as e:
            log.debug(f"HTTP Error ({e.response.status_code}) for {e.response.url}\n{e.response.text}")

        # SERVER RESPONDED OK, BUT POTENTIALLY UNHAPPY DUE TO SERVICE UNAVAILABILITY
        else:
            if "Site Maintenance".casefold() in r.text.casefold():
                MaintenanceState = collections.namedtuple("MaintenanceState", ["response", "reason", "mitigation"])

                site_state_priority = [
                    MaintenanceState(
                        response="Enable service",
                        reason="Your cluster is in Economy Mode.",
                        mitigation="Visit [b blue]{host}[/] to start it.",
                    ),
                    MaintenanceState(
                        response="Estimated time to complete",
                        reason="Your cluster is upgrading.",
                        mitigation="Contact ThoughtSpot with any issues.",
                    ),
                    MaintenanceState(
                        response="Service will be online shortly",
                        reason="Your cluster is starting.",
                        mitigation="Contact ThoughtSpot with any issues.",
                    ),
                ]

                for state in site_state_priority:
                    if state.response in r.text.casefold():
                        break

                # Default state
                else:
                    log.debug(r.text)
                    state = MaintenanceState(
                        response=None,
                        reason="Your cluster is not allowing API access.",
                        mitigation="Check the logs for more details.",
                    )

                raise ThoughtSpotUnavailable(
                    reason=state.reason, mitigation=state.mitigation, host=self.config.thoughtspot.url
                )

            # GOOD TO GO , INTERACT WITH THE APIs
            i = self.api.v1.session_info()
            d = {"__is_session_info__": True, **i.json(), "__url__": self.config.thoughtspot.url}
            self._session_context = SessionContext(environment={}, thoughtspot=d, system={}, user=d)

        return r

    def login(self) -> None:
        """
        Log in to ThoughtSpot.
        """
        # RESET SESSION_CONTEXT IN CASE WE ATTEMPT TO CALL .login MULTIPLE TIMES
        self._session_context = None

        login_info = {"username": self.config.thoughtspot.username}

        if self.config.thoughtspot.is_orgs_enabled:
            login_info["org_id"] = self.config.thoughtspot.default_org
            in_org = f"in org id {self.config.thoughtspot.default_org}"
        else:
            in_org = ""

        #
        # PRIORITY LIST OF AUTHENTICATION MECHANISMS TO ATTEMPT
        #
        attempted_auth_method: dict[str, httpx.Response] = {}

        if self.config.thoughtspot.bearer_token is not None and self._session_context is None:
            log.info(f"Attempting Bearer Token authentication {in_org}")
            self.api._session.headers["Authorization"] = f"Bearer {self.config.thoughtspot.bearer_token}"
            r = self._attempt_do_authenticate(self.api.v2.auth_session_user)
            attempted_auth_method["BEARER_TOKEN_AUTHENTICATION"] = r

            # Bearer Token auth failed, unset the Header.
            if r.is_error:
                self.api._session.headers.pop("authorization")

        if self.config.thoughtspot.secret_key is not None and self._session_context is None:
            log.info(f"Attempting Trusted authentication {in_org}")
            login_info["secret"] = self.config.thoughtspot.secret_key
            r = self._attempt_do_authenticate(self.api.v1._trusted_auth, **login_info)
            attempted_auth_method["TRUSTED_AUTHENTICATION"] = r

            # Trusted auth failed, unset the secret.
            if r.is_error:
                login_info.pop("secret")

        if self.config.thoughtspot.password is not None and self._session_context is None:
            log.info(f"Attempting Basic authentication {in_org}")
            login_info["password"] = self.config.thoughtspot.decoded_password
            r = self._attempt_do_authenticate(self.api.v1.session_login, **login_info)
            attempted_auth_method["BASIC_AUTHENTICATION"] = r

            # Trusted auth failed, unset the password.
            if r.is_error:
                login_info.pop("password")

        try:
            log.debug(f"Session context\n{self.session_context.model_dump()}")
        except errors.NoSessionEstablished:
            for method, r in attempted_auth_method.items():
                log.info(f"Attempted  {method.title().replace('_', ' ')}: HTTP {r.status_code}, see logs for details..")

            raise AuthenticationError(config=self.config) from None

        if (noti := self.session_context.thoughtspot.notification_banner) is not None:
            logger = getattr(log, noti.log_level)

            # Time to be really noisy.
            for line in [_ for _ in noti.message.split(".") if _]:
                logger(line.strip() + ".")

    def logout(self) -> None:
        """
        Log out of ThoughtSpot.
        """
        self.api.v1.session_logout()
