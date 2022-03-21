import datetime as dt
import platform
import logging
import sys

import click

from cs_tools.util import reveal
from cs_tools.api._rest_api_v1 import _RESTAPIv1
from cs_tools._version import __version__
from cs_tools.api.middlewares import (
    AnswerMiddleware, MetadataMiddleware, PinboardMiddleware, SearchMiddleware,
    TagMiddleware, TQLMiddleware, TSLoadMiddleware, UserMiddleware
)
from cs_tools.data.models import ThoughtSpotPlatform, LoggedInUser


log = logging.getLogger(__name__)


class ThoughtSpot:
    """
    """
    def __init__(self, config):
        self.config = config
        self._rest_api = _RESTAPIv1(config, ts=self)

        # Middleware endpoints. These are logically grouped interactions within
        # ThoughtSpot so that working with the REST and GraphQL apis is simpler
        # to do.
        self.search = SearchMiddleware(self)
        self.user = UserMiddleware(self)
        # self.group
        # self.tml
        self.metadata = MetadataMiddleware(self)
        self.pinboard = PinboardMiddleware(self)
        self.answer = AnswerMiddleware(self)
        # self.connection
        # self.worksheet
        # self.table
        self.tag = TagMiddleware(self)
        self.tql = TQLMiddleware(self)
        self.tsload = TSLoadMiddleware(self)

    @property
    def api(self) -> _RESTAPIv1:
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
        r = self.api._session.login(
            username=self.config.auth['frontend'].username,
            password=reveal(self.config.auth['frontend'].password).decode(),
            rememberme=True,
            disableSAMLAutoRedirect=self.config.thoughtspot.disable_sso
        )

        self._logged_in_user = LoggedInUser.from_session_info(r.json())
        self._this_platform = ThoughtSpotPlatform.from_session_info(r.json())

        log.debug(f"""execution context...

        [CS TOOLS COMMAND]
        {click.get_current_context().info_name} {' '.join(sys.argv[1:])}

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
        self.api._session.logout()

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.logout()
