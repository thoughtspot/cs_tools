from __future__ import annotations

from typing import Any, Optional, TextIO, cast
import collections

from rich._loop import loop_last
import httpx
import pydantic
import rich

from cs_tools import _types, datastructures, settings


def _make_error_panel(*, header: str, reason: Optional[str] = None, fixing: Optional[str] = None) -> rich.panel.Panel:
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

    def __init__(
        self,
        *,
        ts_config: settings.CSToolsConfig,
        ctxs: dict[_types.AuthContext, httpx.Response],
        desired_org_id: _types.OrgIdentifier | None = 0,
    ):
        self.ts_config = ts_config
        self.auth_contexts = ctxs
        self.desired_org_id = desired_org_id

    def __rich__(self) -> rich.panel.Panel:
        ts_info = self.ts_config.thoughtspot
        header = f"Authentication failed for [fg-secondary]{self.ts_config.thoughtspot.username}"
        reason = f"{len(self.auth_contexts)} auth contexts {'are' if len(self.auth_contexts) > 1 else 'is'} not valid."
        fixing = []

        if "BEARER_TOKEN" in self.auth_contexts:
            fixing.append("[fg-primary]Bearer Token[/]")
            fixing.append("- Regenerate your Bearer Token in the V2.0 REST API auth/token/full in the Developer tab.")
            fixing.append(f"- Determine if your token is scoped to Org ID {self.desired_org_id}.")
            fixing.append("")

        if "TRUSTED_AUTH" in self.auth_contexts:
            fixing.append("[fg-primary]Trusted Authentication[/]")
            fixing.append(f"- Check if your secret_key is still valid {ts_info.secret_key} in the Developer tab.")
            fixing.append(f"- Determine if your secret_key is scoped to Org ID {self.desired_org_id}.")
            fixing.append("")

        if "BASIC" in self.auth_contexts:
            fixing.append("[fg-primary]Basic Auth[/]")
            fixing.append(
                f"- Check if your username and password are correct from the ThoughtSpot website. You can try them by "
                f"navigating to [fg-secondary]{ts_info.url}?disableSAMLAutoRedirect=true[/]"
            )
            fixing.append("")

        if ts_info.is_orgs_enabled and self.desired_org_id is not None:
            fixing.append(f"- Ensure your User has access to Org ID {self.desired_org_id}.")

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


class ConfigDoesNotExist(CSToolsError):
    """Raised when a CS Tools config can't be found."""

    def __init__(self, config_name: str):
        self.config_name = config_name

    def __rich__(self) -> rich.panel.Panel:
        header = f"Cluster configuration [fg-secondary]{self.config_name}[/] does not exist."
        reason = None
        fixing = None

        return _make_error_panel(header=header, reason=reason, fixing=fixing)


class TSLoadServiceUnreachable(CSToolsError):
    """Raised when the etl_http_server service cannot be reached."""

    def __init__(self, *, httpx_error: httpx.HTTPError, file_descriptor: TextIO, tsload_options: dict[str, Any]):
        self.httpx_error = httpx_error
        self.file_descriptor = file_descriptor
        self.options = tsload_options

    def simulate_tsload_command(self) -> str:
        """Simulate the command that would be run by tsload."""
        command = (
            # THESE ALL ON THE SAME LINE IN THE ERROR MESSAGE
            f"tsload "
            f"--source_file {self.file_descriptor.name} "
            f"--target_database {self.options['target']['database']} "
            f"--target_schema {self.options['target']['schema']} "
            f"--target_table {self.options['target']['table']} "
            f"--max_ignored_rows {self.options['load_options']['max_ignored_rows']} "
            f'--date_format "{self.options["format"]["date_time"]["date_format"]}" '
            f'--time_format "{self.options["format"]["date_time"]["time_format"]}" '
            f'--date_time_format "{self.options["format"]["date_time"]["date_time_format"]}" '
            f'--field_separator "{self.options["format"]["field_separator"]}" '
            f'--null_value "{self.options["format"]["null_value"]}" '
            f"--boolean_representation {self.options['format']['boolean']['true_format']}_{self.options['format']['boolean']['false_format']} "  # noqa: E501
            f'--escape_character "{self.options["format"]["escape_character"]}" '
            f'--enclosing_character "{self.options["format"]["enclosing_character"]}" '
            + ("--skip_second_fraction " if self.options["date_time"].get("skip_second_fraction", False) else "")
            + ("--empty_target " if self.options["load_options"].get("empty_target", False) else "--noempty_target ")
            + ("--has_header_row " if self.options.get("has_header_row", False) else "")
            + ("--flexible" if self.options.get("flexible", False) else "")
        )
        return command

    def __rich__(self) -> rich.panel.Panel:
        header = "The tsload service is unreachable."
        reason = f"HTTP Error: {self.httpx_error}"
        fixing = (
            "Ensure your cluster is set up for allow remote data loads"
            "\n  https://docs.thoughtspot.com/software/latest/tsload-connector#_setting_up_your_cluster"
            "\n\n"
            "If you cannot enable it, here's the tsload command for the file you tried to load:"
            "\n\n"
            f"{self.simulate_tsload_command()}"
        )

        return _make_error_panel(header=header, reason=reason, fixing=fixing)
