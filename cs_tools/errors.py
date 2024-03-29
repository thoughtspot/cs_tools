from typing import Any

from rich.panel import Panel
from rich.text import Text


class CSToolsError(Exception):
    """
    Base Exception class for cs_tools.

    This can be caught to handle any exception raised from this library.
    """

    cli_msg_template = "[b red]{error}[/]"

    def __init__(self, error: str = None, reason: str = None, mitigation: str = None, **ctx: Any):
        self.error = error or self.__class__.error
        self.reason = reason or getattr(self.__class__, "reason", "")
        self.mitigation = mitigation or getattr(self.__class__, "mitigation", "")
        self.extra_context = ctx

    def __rich__(self) -> str:
        m = ""

        if self.__dict__["reason"]:
            m += f"\n[white]{self.__dict__['reason']}[/]"

        if self.__dict__["mitigation"]:
            m += (
                f"\n"
                f"\n[b green]Mitigation[/]"
                f"\n[b yellow]{self.__dict__['mitigation']}[/]"
            )

        text = Panel(
            Text.from_markup(m.format(**self.extra_context)),
            border_style="b red",
            title=self.error.format(**self.extra_context),
            expand=False,
        )

        return text

    def __str__(self) -> str:
        return self.error


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
    reason = "HTTP Error: {http_error.response.status_code} {http_error.response.reason_phrase}"
    mitigation = (
        "Ensure your cluster is set up for allow remove data loads"
        "\n  https://docs.thoughtspot.com/software/latest/tsload-connector#_setting_up_your_cluster"
        "\n\n"
        "Heres the tsload command for the file you tried to load:"
        "\n\n"
        "{tsload_command}"
    )


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
