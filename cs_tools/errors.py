from __future__ import annotations

from typing import Optional, cast
import collections

from rich._loop import loop_last
import pydantic
import rich

from cs_tools import _types, datastructures, settings


def _make_error_panel(*, header: str, reason: str | None = None, fixing: str | None = None) -> rich.panel.Panel:
    """Creates a pretty dialogue for CLI output."""
    content = ""

    if reason is not None:
        content += f"[fg-primary]{reason}[/]"

    if fixing is not None:
        content += f"\n\n[fg-success]Mitigation[/]\n[fg-warn]{fixing}[/]"

    panel = rich.panel.Panel(
        content,
        border_style="fg-error",
        title=header,
        expand=False,
    )

    return panel


class CSToolsError(Exception):
    """
    Base Exception class for cs_tools.

    This can be caught to handle any exception raised from this library.
    """


class ThoughtSpotUnreachable(CSToolsError):
    """
    Raised when ThoughtSpot can't be seen from the local machine.
    """

    def __init__(self, reason, fixing):
        self.reason = reason
        self.fixing = fixing

    def __rich__(self) -> rich.panel.Panel:
        header = "Can't connect to your ThoughtSpot cluster."
        reason = self.reason
        fixing = self.fixing
        return _make_error_panel(header=header, reason=reason, fixing=fixing)


class NoSessionEstablished(CSToolsError):
    """
    Raised when attempting to access ThoughtSpot runtime information
    without a valid session.
    """


class InsufficientPrivileges(CSToolsError):
    """
    Raised when the User cannot perform an action in ThoughtSpot.
    """

    def __init__(
        self, *, user: datastructures.UserInfo, service: str, required_privileges: list[_types.GroupPrivilege]
    ):
        self.user = user
        self.service = service
        self.required_privileges = required_privileges

    def __rich__(self) -> rich.panel.Panel:
        additional_privileges = set(self.required_privileges) - cast(set[_types.GroupPrivilege], self.user.privileges)

        header = f"User {self.user.display_name} cannot access {self.service}."
        reason = f"{self.service} requires the following privileges: {', '.join(self.required_privileges)}"
        fixing = f"Assign at least these privileges to {self.user.display_name}: {', '.join(additional_privileges)}"
        return _make_error_panel(header=header, reason=reason, fixing=fixing)


class AuthenticationFailed(CSToolsError):
    """
    Raised when authentication to ThoughtSpot fails.
    """

    def __init__(self, *, ts_config: settings.CSToolsConfig, desired_org_id: _types.OrgIdentifier | None = 0):
        self.ts_config = ts_config
        self.desired_org_id = desired_org_id

    def __rich__(self) -> rich.panel.Panel:
        ts_info = self.ts_config.thoughtspot
        header = f"Authentication failed for [fg-secondary]{self.ts_config.thoughtspot.username}"
        reason = f"CS Tools config: [fg-secondary]{self.ts_config.name}[/] is not valid."
        fixing = []

        if ts_info.is_orgs_enabled and self.desired_org_id is not None:
            fixing.append(f"Ensure your User has access to Org ID {self.desired_org_id}.")

        if ts_info.bearer_token is not None:
            fixing.append("Regenerate your Bearer Token in the V2.0 REST API auth/token/full in the Developer tab.")

        if ts_info.secret_key is not None:
            fixing.append(f"Check if your secret_key is still valid {ts_info.secret_key} in the Developer tab.")

        if ts_info.password is not None:
            fixing.append("Check if your username and password are correct from the ThoughtSpot website.")
            fixing.append(f"You can try them by navigating to {ts_info.url}?disableSAMLAutoRedirect=true")

        return _make_error_panel(header=header, reason=reason, fixing="\n".join(fixing))


class SyncerInitError(CSToolsError):
    """
    Raised when a Syncer isn't defined correctly.

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

    def __init__(self, protocol: str, pydantic_error: pydantic.ValidationError):
        self.protocol = protocol
        self.pydantic_error = pydantic_error

    @property
    def human_friendly_reason(self) -> str:
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
        ErrorInfo = collections.namedtuple("ErrorInfo", ["user_input", "error_messages"])
        # ErrorInfo(user_input: str, error_messages: list[str])

        # SYNCER ARGS MAY HAVE MULTIPLE VALIDATION ERRORS EACH, SO WE SANITIZE THEM ALL.
        errors: dict[str, ErrorInfo] = {}

        # ==============================
        # CLEAN THE ERRORS FOR NON-TECHNICAL USERS.
        # ==============================
        for error in self.pydantic_error.errors():
            argument_name, *_ = error["loc"]
            assert isinstance(argument_name, str)

            existing_info = errors.get(argument_name, ErrorInfo(user_input="", error_messages=[]))
            messages = existing_info.error_messages
            usr_nput = existing_info.user_input

            # ADD THE USER'S INPUT, IF GIVEN.
            if not usr_nput and error["type"] != "missing":
                usr_nput = error["input"]

            # CLEAN ERROR MESSAGE OF TECHNICAL JARGON.
            JARGON = "Assertion failed, "
            messages.append(error["msg"].replace(JARGON, ""))

            # ADD A NOTE IF THE USER GAVE AN EXTRA ARG NAME.
            if not usr_nput and error["type"] == "extra_forbidden":
                messages[-1] += ". Did you make a typo?"

            errors[argument_name] = ErrorInfo(user_input=usr_nput, error_messages=messages)

        # ==============================
        # FORMAT THE ERRORS FOR DISPLAY.
        # ==============================
        s = len(errors) > 1  # pluralize

        RED_X = "[fg-error]x[/]"

        details = ""

        for is_last_line, (argument_name, error_info) in loop_last(errors.items()):
            details += f"[fg-secondary]{argument_name}[/]"
            details += f"\n[fg-warn]>[/] [fg-success]{error_info.user_input}[/]"

            for error_message in error_info.error_messages:
                details += f"\n{RED_X} {error_message}"

            if not is_last_line:
                details += "\n\n"

        # fmt: off
        phrase = (
            f"\n{len(errors)} argument{'s' if s else ''} ha{'ve' if s else 's'} errors."
            f"\n\n{details}"
        )
        # fmt: on

        return phrase

    def __rich__(self) -> rich.panel.Panel:
        header = f"Your {self.protocol} Syncer encountered an error."
        reason = self.human_friendly_reason
        fixing = (
            # fmt: off
            f"Check the Syncer's documentation page for more information."
            f"\n[fg-secondary]https://thoughtspot.github.io/cs_tools/syncer/{self.protocol.lower()}/"
            # fmt: on
        )

        return _make_error_panel(header=header, reason=reason, fixing=fixing)


#
#
#


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
                "\n[fg-success]Mitigation[/]"
                "\n[fg-warn]{self.mitigation}[/]"
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


#
# Cluster Configurations
#


class ConfigDoesNotExist(CSToolsCLIError):
    title = "Cluster configuration [fg-secondary]{name}[/] does not exist."
