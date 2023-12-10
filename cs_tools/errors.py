from __future__ import annotations

from typing import Optional

import rich


class CSToolsError(Exception):
    """
    Base Exception class for cs_tools.

    This can be caught to handle any exception raised from this library.
    """

    def __init_subclass__(cls):
        super().__init_subclass__()

        if not hasattr(cls, "title"):
            raise RuntimeError("{cls} must supply atleast a .title !")

    def __init__(
        self, title: Optional[str] = None, reason: Optional[str] = None, mitigation: Optional[str] = None, **error_info
    ):
        self.title = title if title is not None else self.__class__.title
        self.reason = reason if reason is not None else getattr(self.__class__, "reason", None)
        self.mitigation = mitigation if mitigation is not None else getattr(self.__class__, "mitigation", None)
        self.error_info = error_info

    def __str__(self) -> str:
        message = "{self.__class__.__name__}: {self.title}"

        if self.reason is not None:
            message += " - {self.reason}"

        if self.mitigation is not None:
            message += " - {self.mitigation}"

        return message.format(self=self, **self.error_info)

    def __rich__(self) -> rich.console.RenderableType:
        error_panel_content = ""

        if self.reason is not None:
            error_panel_content += "[b white]{self.reason}[/]"

        if self.mitigation is not None:
            error_panel_content += "\n" "\n[b green]Mitigation[/]" "\n[b yellow]{self.mitigation}[/]"

        panel = rich.panel.Panel(
            # Double string.format ... for some unknown reason.
            error_panel_content.format(self=self, **self.error_info).format(self=self, **self.error_info),
            border_style="b red",
            title=self.title.format(**self.error_info),
            expand=False,
        )

        return panel


class ThoughtSpotUnreachable(CSToolsError):
    """Raised when ThoughtSpot can't be seen from the local machine."""

    title = "Can't connect to your ThoughtSpot cluster."


class ThoughtSpotUnavailable(CSToolsError):
    """Raised when a ThoughtSpot session can't be established."""

    title = "Your ThoughtSpot cluster is currently unavailable."


class AuthenticationError(CSToolsError):
    """Raised when incorrect authorization details are supplied."""

    title = "Authentication failed for [b blue]{config.thoughtspot.username}"
    reason = "\nCS Tools config: [b blue]{config.name}[/]" "\n    Incident ID: [b blue]{incident_id}[/]"
    mitigation = (
        "\n1/ Check if your password is correct." "\n2/ Determine if your usename ends with a whitelisted email domain."
    )


class TSLoadServiceUnreachable(CSToolsError):
    """Raised when the etl_http_server service cannot be reached."""

    title = "The tsload service is unreachable."
    reason = "HTTP Error: {http_error.response.status_code} {http_error.response.reason_phrase}"
    mitigation = (
        "Ensure your cluster is set up for allow remote data loads"
        "\n  https://docs.thoughtspot.com/software/latest/tsload-connector#_setting_up_your_cluster"
        "\n\n"
        "If you cannot enable it, here's the tsload command for the file you tried to load:"
        "\n\n"
        "{tsload_command}"
    )


class ContentDoesNotExist(CSToolsError):
    """Raised when ThoughtSpot can't find content by this name or guid."""

    title = "No {type} found."


class AmbiguousContentError(CSToolsError):
    """Raised when ThoughtSpot can't determine an exact content match."""

    title = "Multiple {type}s found with the name [blue]{name}."


class InsufficientPrivileges(CSToolsError):
    """Raised when the User cannot perform an action."""

    title = "User [b blue]{user.display_name}[/] does not have enough privilege to access {service}."
    reason = (
        "{user.display_name} requires the {required_privileges} privilege(s)."
        "\nPlease consult with your ThoughtSpot Administrator."
    )


#
# Syncer
#


class SyncerProtocolError(CSToolsError):
    """Raised when a Custom Syncer breaks the contract."""

    title = "Custom Syncer could not be created."


class SyncerError(CSToolsError):
    """Raised when a Syncer isn't defined correctly."""

    title = "Your {proto} syncer encountered an error."


#
# Cluster Configurations
#


class ConfigDoesNotExist(CSToolsError):
    title = "Cluster configuration [b blue]{name}[/] does not exist."
