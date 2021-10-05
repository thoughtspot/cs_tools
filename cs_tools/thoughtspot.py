from ._rest_api_v1 import _RESTAPIv1
from ._schema import ThoughtSpotPlatform, LoggedInUser


class ThoughtSpot:
    """
    """
    def __init__(self, config):
        self.config = config
        self._rest_api = _RESTAPIv1(config, ts=self)

        # Middleware methods. These are logically grouped interactions within
        # ThoughtSpot so that working with the REST and GraphQL apis is simpler
        # to do.
        # self.user
        # self.group
        # self.tml
        # self.pinboard
        # self.answer
        # self.connection
        # self.worksheet
        # self.table
        # self.tag

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
        r = self._rest_api.login()
        self._logged_in_user = LoggedInUser.from_session_info(r.json())
        self._this_platform = ThoughtSpotPlatform.from_session_info(r.json())

    def logout(self) -> None:
        """
        Log out of ThoughtSpot.
        """
        self._rest_api.logout()

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.logout()
