
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


class TSLoadServiceUnreachable(CSToolsException):
    """
    Raise when the etl_http_server service cannot be reached.
    """
    def __init__(self, message, http_error):
        self.http_error = http_error
        super().__init__(message)


class AuthenticationError(CSToolsException):

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
