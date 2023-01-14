from typing import Any


class CSToolsError(Exception):
    """
    Base Exception class for cs_tools.

    This can be caught to handle any exception raised from this library.
    """

    cli_msg_template = "{error}"

    def __init__(self, error: str = None, reason: str = None, mitigation: str = None, **ctx: Any):
        self.__dict__ = {
            "error": error or self.__class__.error,
            "reason": reason or getattr(self.__class__, "reason", ""),
            "mitigation": mitigation or getattr(self.__class__, "mitigation", ""),
            **ctx,
        }

    def __str__(self) -> str:
        msg = self.cli_msg_template

        if self.__dict__["reason"]:
            msg += "\n[white]{reason}"

        if self.__dict__["mitigation"]:
            msg += "\n\n[secondary]Mitigation\n[hint]{mitigation}"

        # double expand __dict__ to template anything within cli_msg_template
        return msg.format(**self.__dict__).format(**self.__dict__)


class ThoughtSpotUnavailable(CSToolsError):
    """
    Raised when ThoughtSpot can't be reached.
    """

    error = "Your ThoughtSpot cluster is currently unavailable."


class TSLoadServiceUnreachable(CSToolsError):
    """
    Raised when the etl_http_server service cannot be reached.
    """

    error = "The remote tsload service ([blue]etl_httpserver[/]) is unreachable."


class ContentDoesNotExist(CSToolsError):
    """
    Raised when ThoughtSpot can't find content by this name or guid.
    """

    error = "No {type} found."


class AmbiguousContentError(CSToolsError):
    """
    Raised when ThoughtSpot can't determine an exact content match.
    """

    error = "Multiple {type}s found with the name [blue]{name}."


class InsufficientPrivileges(CSToolsError):
    """
    Raised when the User cannot perform an action.
    """

    error = "User [blue]{user.display_name}[/] does not have the correct privileges to " "access {service}."
    reason = (
        "{user.display_name} requires the {required_privileges} privilege."
        "\nPlease consult with your ThoughtSpot Administrator."
    )


class AuthenticationError(CSToolsError):
    """
    Raised when the ThoughtSpot platform is unreachable.
    """

    error = "Authentication failed for [blue]{config_username}"
    reason = "{debug}" "\n" "\nCS Tools config: {config_name}" "\n    Incident ID: {incident_id}"


#
# Syncer
#


class SyncerProtocolError(CSToolsError):
    """
    Raised when a Custom Syncer breaks the contract.
    """

    error = "Custom Syncer could not be created."


class SyncerError(CSToolsError):
    """
    Raised when a Syncer isn't defined correctly.
    """

    error = "Your {proto} syncer encountered an error."


#
# Cluster Configurations
#


class ConfigDoesNotExist(CSToolsError):
    error = "Cluster configuration [blue]{name}[/] does not exist."
