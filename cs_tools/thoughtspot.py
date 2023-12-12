from __future__ import annotations

from typing import TYPE_CHECKING
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
    """ """

    def __init__(self, config: CSToolsConfig, auto_login: bool = False):
        self.config = config
        self.api = RESTAPIClient(ts_url=str(config.thoughtspot.url), verify=config.thoughtspot.disable_ssl)

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
    def session_context(self):  # -> SessionContext:
        """Returns information about the ThoughtSpot session."""
        if not hasattr(self, "_session_context"):
            raise errors.NoSessionEstablished()

        return self._session_context

    def login(self) -> None:
        """
        Log in to ThoughtSpot.
        """
        login_info = {"username": self.config.thoughtspot.username}

        if self.config.thoughtspot.is_orgs_enabled:
            login_info["org_id"] = self.config.thoughtspot.org_id

        if self.config.thoughtspot.secret_key is not None:
            login_info["secret"] = self.config.thoughtspot.secret_key
            authentication_method = self.api.v1._trusted_auth
        else:
            login_info["password"] = self.config.thoughtspot.decoded_password
            authentication_method = self.api.v1.session_login

        try:
            r = authentication_method(**login_info)
            r.raise_for_status()

        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            if "SSL: CERTIFICATE_VERIFY_FAILED" in str(e):
                exc_info = {
                    "reason": "Outdated Python default certificate detected.",
                    "mitigation": (
                        f"Quick fix: run [b blue]cs_tools config modify --config {self.config.name} --disable_ssl[/] "
                        f"and try again.\n\nLonger fix: try running [b blue]cs_tools self pip install certifi "
                        f"--upgrade[/] and try again."
                    ),
                }
            else:
                exc_info = {
                    "reason": (
                        f"Cannot connect to ThoughtSpot ( [b blue]{self.config.thoughtspot.url}[/] ) from your "
                        f"computer"
                    ),
                    "mitigation": f"Does your ThoughtSpot require a VPN to connect?\n\n[white]>>>[/] {e}",
                }

            raise errors.ThoughtSpotUnreachable(**exc_info) from None

        except httpx.HTTPStatusError as e:
            if r.status_code == httpx.codes.UNAUTHORIZED:
                incident_id = r.json().get("incident_id", "<missing>")
                raise AuthenticationError(config=self.config, incident_id=incident_id) from None
            raise e

        # authentication_method() .is_success , but the instance is unavailable for reasons
        else:
            if "Site Maintenance".casefold() in r.text.casefold():
                site_states = [
                    ("Enable service", "Your cluster is in Economy Mode.", "Visit [b blue]{host}[/] to start it."),
                    (
                        "Service will be online shortly",
                        "Your cluster is starting.",
                        "Contact ThoughtSpot with any issues.",
                    ),
                    (
                        "Estimated time to complete",
                        "Your cluster is upgrading.",
                        "Contact ThoughtSpot with any issues.",
                    ),
                ]

                for page_response, rzn, fwd in site_states:  # noqa: B007
                    if page_response.casefold() in r.text.casefold():
                        break
                else:
                    rzn = "Your cluster is not allowing API access."
                    fwd = "Check the logs for more details."
                    log.debug(r.text)

                raise ThoughtSpotUnavailable(reason=rzn, mitigation=fwd, host=self.config.thoughtspot.url)

        # ==============================================================================================================
        # GOOD TO GO , INTERACT WITH THE APIs
        # ==============================================================================================================
        r = self.api.v1.session_info()
        d = {"__is_session_info__": True, **r.json(), "__url__": self.config.thoughtspot.url}
        self._session_context = SessionContext(environment={}, thoughtspot=d, system={}, user=d)
        log.debug(self._session_context.dict())

    def logout(self) -> None:
        """
        Log out of ThoughtSpot.
        """
        self.api.v1.session_logout()
