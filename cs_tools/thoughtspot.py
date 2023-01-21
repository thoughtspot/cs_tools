from __future__ import annotations

import platform
import datetime as dt
import logging
import json
import sys

import httpx

from cs_tools.api._rest_api_v1 import RESTAPIv1
from cs_tools.api.middlewares import (
    LogicalTableMiddleware,
    PinboardMiddleware,
    MetadataMiddleware,
    TSLoadMiddleware,
    SearchMiddleware,
    AnswerMiddleware,
    GroupMiddleware,
    UserMiddleware,
    TMLMiddleware,
    TQLMiddleware,
    TagMiddleware,
    OrgMiddleware,
)
from cs_tools.settings import CSToolsConfig
from cs_tools._version import __version__
from cs_tools.errors import ThoughtSpotUnavailable, AuthenticationError
from cs_tools.types import ThoughtSpotPlatform, LoggedInUser
from cs_tools import utils

log = logging.getLogger(__name__)


class ThoughtSpot:
    """ """

    def __init__(self, config: CSToolsConfig):
        self.config = config
        self._rest_api_v1 = RESTAPIv1(config.thoughtspot.fullpath, verify=config.thoughtspot.disable_ssl)
        # self._rest_api_v2 = RESTAPIv2()

        # assigned at self.login()
        self._logged_in_user: LoggedInUser = None
        self._platform: ThoughtSpotPlatform = None

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

    @property
    def api(self) -> RESTAPIv1:
        """
        Access the REST API.
        """
        return self._rest_api_v1

    @property
    def me(self) -> LoggedInUser:
        """
        Return information about the logged in user.
        """
        if not hasattr(self, "_logged_in_user"):
            raise RuntimeError("attempted to access user details before logging into the " "ThoughtSpot platform")

        return self._logged_in_user

    @property
    def platform(self) -> ThoughtSpotPlatform:
        """
        Return information about the ThoughtSpot platform.
        """
        if not hasattr(self, "_this_platform"):
            raise RuntimeError("attempted to access platform details before logging into the " "ThoughtSpot platform")

        return self._this_platform

    def login(self) -> None:
        """
        Log in to ThoughtSpot.
        """

        try:
            r = self.api.session_login(
                username=self.config.auth["frontend"].username,
                password=utils.reveal(self.config.auth["frontend"].password).decode(),
                # disableSAMLAutoRedirect=self.config.thoughtspot.disable_sso
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == httpx.codes.UNAUTHORIZED:
                raise AuthenticationError(
                    config_name=self.config.name,
                    config_username=self.config.auth["frontend"].username,
                    debug="".join(json.loads(e.response.json().get("debug", []))),
                    incident_id=e.response.json().get("incident_id_guid", "<missing>"),
                )
            raise e

        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            rzn = "Cannot connect to ThoughtSpot ( [b blue]{host}[/] ) from your computer"
            fwd = "Is your [white]ThoughtSpot[/] accessible outside of the VPN? \n\n[white]>>>[/] {exc}"
            raise ThoughtSpotUnavailable(reason=rzn, mitigation=fwd, host=self.config.thoughtspot.host, exc=e) from None

        # .session_login() returns 200 OK , but the instance is unavailable for the API
        if "Site Maintenance".casefold() in r.text.casefold():
            site_states = [
                ("Enable service", "Your cluster is in Economy Mode.", "Visit [b blue]{host}[/] to start it."),
                ("Service will be online shortly", "Your cluster is starting.", "Contact ThoughtSpot with any issues."),
            ]

            for page_response, rzn, fwd in site_states:
                if page_response.casefold() in r.text.casefold():
                    break
            else:
                rzn = "Your cluster is not allowing API access."
                fwd = "Check the logs for more details."
                log.debug(r.text)

            raise ThoughtSpotUnavailable(reason=rzn, mitigation=fwd, host=self.config.thoughtspot.host)

        # ==============================================================================================================
        # GOOD TO GO , INTERACT WITH THE APIs
        # ==============================================================================================================

        r = self.api.session_info()
        d = r.json()

        self._logged_in_user = LoggedInUser.from_api_v1_session_info(d)
        self._this_platform = ThoughtSpotPlatform.from_api_v1_session_info(d)

        log.debug(
            f"""execution context...

        [CS TOOLS COMMAND]
        cs_tools {' '.join(sys.argv[1:])}

        [PLATFORM DETAILS]
        system: {platform.system()} (detail: {platform.platform()})
        python: {platform.python_version()}
        ran at: {dt.datetime.now(dt.timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S%z')}
        cs_tools: v{__version__}

        [THOUGHTSPOT]
        cluster id: {self._this_platform.cluster_id}
        cluster: {self._this_platform.cluster_name}
        url: {self._this_platform.url}
        timezone: {self._this_platform.timezone}
        branch: {self._this_platform.deployment}
        version: {self._this_platform.version}

        [LOGGED IN USER]
        user_id: {self._logged_in_user.guid}
        username: {self._logged_in_user.username}
        display_name: {self._logged_in_user.display_name}
        privileges: {list(map(str, self._logged_in_user.privileges))}
        """
        )

    def logout(self) -> None:
        """
        Log out of ThoughtSpot.
        """
        self.api.session_logout()
