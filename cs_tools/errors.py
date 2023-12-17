from __future__ import annotations

from typing import Optional
import collections

import pydantic
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
        extra_info = {"self": self, **self.error_info}

        if self.reason is not None:
            error_panel_content += "[b white]{self.reason}[/]".format(**extra_info)

        if self.mitigation is not None:
            # fmt: off
            error_panel_content += (
                "\n"
                "\n[b green]Mitigation[/]"
                "\n[b yellow]{self.mitigation}[/]"
            )
            # fmt: on

        panel = rich.panel.Panel(
            # Double .format() because f-string replacement is not recursive until 3.12
            error_panel_content.format(**extra_info).format(**extra_info),
            border_style="b red",
            title=self.title.format(**extra_info),
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
    # fmt: off
    reason = (
        "\nCS Tools config: [b blue]{config.name}[/]"
        "\n    Incident ID: [b blue]{incident_id}[/]"
    )
    # fmt: on
    mitigation = (
        "\n1/ Check if your username and password is correct from the ThoughtSpot website."
        "\n2/ Determine if your usename ends with a whitelisted email domain."
        "\n3/ If your password contains a [b green]$[/] or [b green]![/], run [b green]cs_tools config modify "
        "--config {config.thoughtspot.username} --password prompt[/] and type your password in the hidden prompt."
        "\n"
        "\n[b green]**[/]you may need to use [b green]{config.thoughtspot.url}?disableAutoSAMLRedirect=true[/] to see "
        "the login page."
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


class SyncerInitError(CSToolsError):
    """Raised when a Syncer isn't defined correctly."""

    title = "Your {proto} Syncer encountered an error."
    mitigation = (
        # fmt: off
        "Check the Syncer's documentation page for more information."
        "\n[b blue]https://thoughtspot.github.io/cs_tools/syncer/{proto}/"
        # fmt: on
    )

    def __init__(self, pydantic_error: pydantic.ValidationError, *, proto: str):
        self.pydantic_error = pydantic_error
        self.error_info = {"proto": proto or pydantic_error.title}

    @property
    def reason(self) -> str:
        argument_block = collections.defaultdict(list)

        for error_info in self.pydantic_error.errors():
            key = f"{error_info['loc'][0]}\n[b blue]{error_info['input']}[/]" if error_info["loc"] else "__root__"
            argument_block[key].append(f"x {error_info['msg']}")

        if self.pydantic_error.error_count() > 1:
            s = "s"
            v = "ve"
        else:
            s = ""
            v = "s"

        error_messages = ""

        for argument, errors in argument_block.items():
            error_messages += f"\n{argument}"

            for error in errors:
                error_messages += f"\n[b red]{error}[/]"

        # fmt: off
        phrase = (
            f"\n{self.pydantic_error.error_count()} argument{s} ha{v} errors."
            f"\n{error_messages}"
        )
        # fmt: on

        return phrase


#
# Cluster Configurations
#


class ConfigDoesNotExist(CSToolsError):
    title = "Cluster configuration [b blue]{name}[/] does not exist."
