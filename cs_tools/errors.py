from __future__ import annotations

from typing import Optional
import collections

from rich._loop import loop_last
import pydantic
import rich


class CSToolsError(Exception):
    """
    Base Exception class for cs_tools.

    This can be caught to handle any exception raised from this library.
    """


class NoSessionEstablished(CSToolsError):
    """
    Raised when attempting to access ThoughtSpot runtime information
    without a valid session.
    """


class CSToolsCLIError(CSToolsError):
    """When raised, will present a pretty error to the CLI."""

    # DEV NOTE: @boonhapus, 2023/12/18
    #
    # This can be refactored so that subclasses require only to
    # implement the __rich__ protocol. It will allow us to have CLI
    # errors and Library errors. CLI errors must implement __rich__ and
    # have their return type be a rich.panel.Panel
    #

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

    def __rich__(self) -> rich.panel.Panel:
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


class ThoughtSpotUnreachable(CSToolsCLIError):
    """Raised when ThoughtSpot can't be seen from the local machine."""

    title = "Can't connect to your ThoughtSpot cluster."


class ThoughtSpotUnavailable(CSToolsCLIError):
    """Raised when a ThoughtSpot session can't be established."""

    title = "Your ThoughtSpot cluster is currently unavailable."


class AuthenticationError(CSToolsCLIError):
    """Raised when incorrect authorization details are supplied."""

    title = "Authentication failed for [b blue]{config.thoughtspot.username}"
    reason = "\nCS Tools config: [b blue]{config.name}[/]"
    # fmt: off
    mitigation = (
        "\n[b white]1/[/] Check if your username and password is correct from the ThoughtSpot website."
        "\n[b white]2/[/] Determine if your usename ends with a whitelisted email domain."
        "\n[b white]3/[/] If your password contains a [b green]$[/] or [b green]![/], run this command and type your "
        "password in the hidden prompt."
        "\n   [b green]cs_tools config modify --config {config.name} --password prompt[/]"
        "\n[b white]4/[/] If your cluster is orgs-enabled, ensure you can access the specified org id."
        "\n"
        "\n   [b green]**[/] you may need to use this url to see the login page"
        "\n   [b green]{config.thoughtspot.url}?disableAutoSAMLRedirect=true[/]"
    )
    # fmt: on


class TSLoadServiceUnreachable(CSToolsCLIError):
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


class ContentDoesNotExist(CSToolsCLIError):
    """Raised when ThoughtSpot can't find content by this name or guid."""

    title = "No {type} found."


class AmbiguousContentError(CSToolsCLIError):
    """Raised when ThoughtSpot can't determine an exact content match."""

    title = "Multiple {type}s found with the name [blue]{name}."


class InsufficientPrivileges(CSToolsCLIError):
    """Raised when the User cannot perform an action."""

    title = "User [b blue]{user.display_name}[/] does not have enough privilege to access {service}."
    reason = (
        "{user.display_name} requires the {required_privileges} privilege(s)."
        "\nPlease consult with your ThoughtSpot Administrator."
    )


#
# Syncer
#


class SyncerInitError(CSToolsCLIError):
    """Raised when a Syncer isn't defined correctly."""

    """
     ╭──────── Your Starburst Syncer encountered an error. ────────╮
     │                                                             │
     │ 2 arguments have errors.                                    │
     │                                                             │
     │ catalog                                                     │
     │ x Field required                                            │
     │                                                             │
     │ secret                                                      │
     │ x Field required, you must provide a json web token         │
     │                                                             │
     │ Mitigation                                                  │
     │ Check the Syncer's documentation page for more information. │
     │ https://thoughtspot.github.io/cs_tools/syncer/starburst/    │
     ╰─────────────────────────────────────────────────────────────╯
    """

    title = "Your {proto} Syncer encountered an error."
    mitigation = (
        # fmt: off
        "Check the Syncer's documentation page for more information."
        "\n[b blue]https://thoughtspot.github.io/cs_tools/syncer/{proto_lower}/"
        # fmt: on
    )

    def __init__(self, pydantic_error: pydantic.ValidationError, *, proto: str):
        self.pydantic_error = pydantic_error
        self.error_info = {"proto": proto, "proto_lower": proto.lower()}

    @property
    def reason(self) -> str:  # type: ignore[override]
        """
        Responsible for showing arguments and their errors.

        │ 2 arguments have errors.                                    │
        │                                                             │
        │ catalog                                                     │
        │ x Field required                                            │
        │                                                             │
        │ secret                                                      │
        │ x Field required, you must provide a json web token         │
        """
        errors: dict[str, list[str]] = collections.defaultdict(list)

        for error in self.pydantic_error.errors():
            argument_name, *_ = error["loc"]
            assert isinstance(argument_name, str)

            # Clean error message of technical jargon.
            message = error["msg"].replace("Assertion failed, ", "")

            # Add the user's input, if given.
            if error["type"] != "missing":
                message += f" [b yellow](given: [b green]{error['input']}[/])[/]"

            errors[argument_name].append(message)

        summary = "1 argument has" if len(errors) == 1 else f"{len(errors)} arguments have"
        details = ""

        for is_last_error, (argument, lines) in loop_last(errors.items()):
            details += f"[b blue]{argument}[/]"

            for line in lines:
                details += f"\n[b red]x[/] {line}"

            if not is_last_error:
                details += "\n\n"

        # fmt: off
        phrase = (
            f"\n{summary} errors."
            f"\n\n{details}"
        )
        # fmt: on

        return phrase


#
# Cluster Configurations
#


class ConfigDoesNotExist(CSToolsCLIError):
    title = "Cluster configuration [b blue]{name}[/] does not exist."
