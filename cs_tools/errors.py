
class CSToolsException(Exception):
    """
    Base class for cs_tools.

    This can be caught to handle any exception raise from this library.
    """


class ContentDoesNotExist(CSToolsException):
    """
    Raised when ThoughtSpot can't find content by this name or guid.
    """
    def __init__(self, type: str, name: str = None, guid: str = None, reason: str = None):
        self.type = type
        self.guid = guid
        self.name = name
        self.reason = reason
        super().__init__(self.message)

    @property
    def message(self) -> str:
        """
        Exception reason.
        """
        if self.reason is not None:
            return f"No {self.type} found for {self.reason}"

        if self.guid is not None:
            return f"No {self.type} found with guid '{self.guid}'"

        if self.name is not None:
            return f"No {self.type} found with name '{self.name}'"


class AmbiguousContentError(CSToolsException):
    """
    Raised when ThoughtSpot can't determine an exact content match.
    """
    def __init__(self, name: str, type: str = None):
        self.name = name
        self.type = type
        super().__init__(self.message)

    @property
    def message(self) -> str:
        """
        Exception reason.
        """
        if self.type is not None:
            objects = f'{self.type}s'
        else:
            objects = 'objects'

        return f"Multiple {objects} found with name '{self.name}'"


class InsufficientPrivileges(CSToolsException):
    """
    Raised when the User cannot perform an action.
    """
    def __init__(self, *, user, service, required_privileges):
        self.user = user
        self.service = service
        self.required_privileges = required_privileges

    @property
    def message(self) -> str:
        p = ', '.join(self.required_privileges)
        s = (
            f'[red]User {self.user.display_name} do not have the correct privileges to '
            f'access the {self.service} service!\n\nYou require the {p} privilege.\n\n'
            f'Please consult with your ThoughtSpot Administrator.[/]'
        )
        return s


class TSLoadServiceUnreachable(CSToolsException):
    """
    Raised when the etl_http_server service cannot be reached.
    """
    def __init__(self, message, http_error):
        self.http_error = http_error
        super().__init__(message)


class AuthenticationError(CSToolsException):
    """
    Raised when the ThoughtSpot platform is unreachable.
    """
    def __init__(self, *, username: str):
        self.username = username

    @property
    def message(self) -> str:
        """
        Exception reason.
        """
        return f'Authentication failed for {self.username}.'


class CertificateVerifyFailure(CSToolsException):
    """
    """

    @property
    def warning(self) -> str:
        return 'SSL verify failed, did you mean to use flag --disable_ssl?'


class TableAlreadyExists(Exception):
    """
    """
