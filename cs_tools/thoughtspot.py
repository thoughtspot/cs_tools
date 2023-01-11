from __future__ import annotations
import datetime as dt
import platform
import logging
import json
import sys

import httpx

from cs_tools.api._rest_api_v1 import RESTAPIv1
from cs_tools.api.middlewares import Answer, Connection, Group, Metadata, Org, Pinboard, Search, Tag, TQL, TSLoad, User
from cs_tools._version import __version__
from cs_tools.settings import CSToolsConfig
from cs_tools.errors import ThoughtSpotUnavailable, AuthenticationError
from cs_tools.types import ThoughtSpotPlatform, LoggedInUser
from cs_tools.util import reveal


log = logging.getLogger(__name__)


class ThoughtSpot:
    """
    """
    def __init__(self, config: CSToolsConfig):
        self.config = config
        self._rest_api_v1 = RESTAPIv1(config.thoughtspot.fullpath, verify=config.verify, )
        # self._rest_api_v2 = RESTAPIv2()

        # assigned at self.login()
        self._logged_in_user: LoggedInUser = None
        self._platform: ThoughtSpotPlatform = None

        # ==============================================================================
        # API MIDDLEWARES: logically grouped API interactions within ThoughtSpot
        # ==============================================================================
        self.org = Org(self)
        self.search = Search(self)
        self.user = User(self)
        self.group = Group(self)
        # self.tml
        self.metadata = Metadata(self)
        self.pinboard = self.liveboard = Pinboard(self)
        self.answer = Answer(self)
        self.connection = Connection(self)
        # self.worksheet
        # self.table
        self.tag = Tag(self)
        self.tql = TQL(self)
        self.tsload = TSLoad(self)

    @property
    def api(self) -> RESTAPIv1:
        """
        Access the REST API.
        """
        return self._rest_api

    @property
    def me(self) -> LoggedInUser:
        """
        Return information about the logged in user.
        """
        if not hasattr(self, '_logged_in_user'):
            raise RuntimeError(
                'attempted to access user details before logging into the '
                'ThoughtSpot platform'
            )

        return self._logged_in_user

    @property
    def platform(self) -> ThoughtSpotPlatform:
        """
        Return information about the ThoughtSpot platform.
        """
        if not hasattr(self, '_this_platform'):
            raise RuntimeError(
                'attempted to access platform details before logging into the '
                'ThoughtSpot platform'
            )

        return self._this_platform

    def login(self) -> None:
        """
        Log in to ThoughtSpot.
        """
        try:
            r = self.api.session_login(
                username=self.config.auth['frontend'].username,
                password=reveal(self.config.auth['frontend'].password).decode(),
                # disableSAMLAutoRedirect=self.config.thoughtspot.disable_sso
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == httpx.codes.UNAUTHORIZED:
                raise AuthenticationError(
                    config_name=self.config.name,
                    config_username=self.config.auth['frontend'].username,
                    debug=''.join(json.loads(e.response.json().get('debug', []))),
                    incident_id=e.response.json().get('incident_id_guid', '<missing>')
                )
            raise e
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            host = self.config.thoughtspot.host
            rzn = (
                f'cannot see url [blue]{host}[/] from the current machine'
                f'\n\n>>> [yellow]{e}[/]'
            )
            raise ThoughtSpotUnavailable(reason=rzn) from None

        # got a response, but couldn't make sense of it
        try:
            data = r.json()
        except json.JSONDecodeError:
            if 'Enter the activation code to enable service' in r.text:
                info = {
                    'reason': "It is in 'Economy Mode'.",
                    'mitigation': f'Activate it at [url]{self.config.thoughtspot.host}'
                }
            else:
                info = {'reason': 'for an unknown reason.'}

            raise ThoughtSpotUnavailable(**info) from None

        self._logged_in_user = LoggedInUser.from_api_v1_session_info(data)
        self._this_platform = ThoughtSpotPlatform.from_api_v1_session_info(data)

        log.debug(f"""execution context...

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
        username: {self._logged_in_user.name}
        display_name: {self._logged_in_user.display_name}
        privileges: {list(map(str, self._logged_in_user.privileges))}
        """)

    def logout(self) -> None:
        """
        Log out of ThoughtSpot.
        """
        self.api.session_logout.logout()
