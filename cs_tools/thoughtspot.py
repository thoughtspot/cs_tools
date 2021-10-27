from cs_tools.helpers.secrets import reveal

from ._rest_api_v1 import _RESTAPIv1
from .middlewares import (
    AnswerMiddleware, PinboardMiddleware, SearchMiddleware, TagMiddleware
)
from ._schema import ThoughtSpotPlatform, LoggedInUser


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
        # self.user
        # self.group
        # self.tml
        self.pinboard = PinboardMiddleware(self)
        self.answer = AnswerMiddleware(self)
        # self.connection
        # self.worksheet
        # self.table
        self.tag = TagMiddleware(self)

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
