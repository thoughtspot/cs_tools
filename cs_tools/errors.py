import json

import httpx

from cs_tools.settings import TSConfig


class CSToolsException(Exception):
    """
    Base class for cs_tools.

    This can be caught to handle any exception raised from this library.
    """

    @property
    def cli_message(self) -> str:
        """
        Output for the command line interface.

        This is oftentimes meant to be a simplified message, friendlier UX, or
        offer a path for resolution.
        """
        raise NotImplementedError('all cs_tools exceptions must add .cli_message')


class ThoughtSpotUnreachable(CSToolsException):
    """
    Raised when ThoughtSpot can't be reached.
    """
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(self.cli_message)

    @property
    def cli_message(self) -> str:
        return f'Your ThoughtSpot cluster is unreachable: {self.reason}'


class TSLoadServiceUnreachable(CSToolsException):
    """
    Raised when the etl_http_server service cannot be reached.
    """
    def __init__(self, reason, http_error):
        self.http_error = http_error
        self.reason = reason
        super().__init__(self.cli_message)

    @property
    def cli_message(self) -> str:
        return f'The remote tsload service (etl_http_server) is unreachable: {self.reason}'


class ContentDoesNotExist(CSToolsException):
    """
    Raised when ThoughtSpot can't find content by this name or guid.
    """
    def __init__(self, type: str, name: str = None, guid: str = None, reason: str = None):
        self.type = type
        self.guid = guid
        self.name = name
        self.reason = reason
        super().__init__(self.cli_message)

    @property
    def cli_message(self) -> str:
        msg = f'No {self.type} found'
        if self.reason is not None:
            msg += f" for {self.reason}"

        if self.guid is not None:
            msg += f" with guid '{self.guid}'"

        if self.name is not None:
            msg += f" with name '{self.name}'"

        return msg


class AmbiguousContentError(CSToolsException):
    """
    Raised when ThoughtSpot can't determine an exact content match.
    """
    def __init__(self, name: str, type: str = None):
        self.name = name
        self.type = type
        super().__init__(self.cli_message)

    @property
    def cli_message(self) -> str:
        objects = f'{self.type}s' if self.type is not None else 'objects'
        return f"Multiple {objects} found with name '{self.name}'"


class InsufficientPrivileges(CSToolsException):
    """
    Raised when the User cannot perform an action.
    """
    def __init__(self, *, user, service, required_privileges):
        self.user = user
        self.service = service
        self.required_privileges = required_privileges
        super().__init__(self.cli_message)

    @property
    def cli_message(self) -> str:
        p = ', '.join(self.required_privileges)
        s = (
            f'User {self.user.display_name} do not have the correct privileges to '
            f'access the {self.service} service!\n\nYou require the {p} privilege.\n\n'
            f'Please consult with your ThoughtSpot Administrator.'
        )
        return s


class AuthenticationError(CSToolsException):
    """
    Raised when the ThoughtSpot platform is unreachable.
    """
    def __init__(self, ts_config: TSConfig, *, original: httpx.HTTPStatusError):
        self.ts_config = ts_config
        self.original_exception = original
        super().__init__(self.cli_message)

    @property
    def cli_message(self) -> str:
        r = self.original_exception.response.json()
        incident = r['incident_id_guid']
        msg = ' '.join(json.loads(r['debug']))

        http_code = self.original_exception.response.status_code
        user = self.ts_config.auth['frontend'].username
        name = self.ts_config.name

        return (
            f'Authentication failed ({http_code}) for [blue]{user}[/][red]'
            f'\n\n  {msg}[/][yellow]'
            f'\n\n  CS Tools config: {name}'
            f'\n      Incident ID: {incident}'
        )


class CertificateVerifyFailure(CSToolsException):
    """
    Raised when SSL certificate verification fails.
    """
    def __init__(self, ts_config):
        self.ts_config = ts_config
        super().__init__(self.cli_message)

    @property
    def cli_message(self) -> str:
        name = self.ts_config.name

        return (
            'Local SSL certificate verification failed. If this continues to happen, '
            'try running:'
            f'\n\n  [yellow]cs_tools config modify --config {name} --disable_ssl[/]'
        )


class TableAlreadyExists(Exception):
    """
    """

    @property
    def cli_message(self) -> str:
        return str(self)
