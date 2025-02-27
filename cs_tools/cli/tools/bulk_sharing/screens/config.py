# ruff: noqa: RUF012
from __future__ import annotations

from typing import Literal, Optional
import asyncio
import logging

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Header
import httpx

from cs_tools.api import workflows
from cs_tools.cli.tools.bulk_sharing.widgets import button_grid

log = logging.getLogger(__name__)


class SecurityConfig(Screen):
    DEFAULT_CSS = """
    SecurityConfig {
        # Center everything on screen.
        align: center middle;
    }

    .bottom-hero {
        # height: auto;
    }

    # Buttons should take up equal sizes of the bottom hero section.
    .btn-submit, .btn-fetch {
        width: 45%;
        margin: 0 5 0 5;
    }
    """

    def compose(self) -> ComposeResult:
        SecurityConfig.TITLE = self.app.active_table["metadata_header"]["name"]

        cols = [_["metadata_header"]["displayName"] for _ in self.app.active_groups]
        rows = [_["header"]["name"] for _ in self.app.active_table["metadata_detail"]["columns"]]
        grid = button_grid.ButtonGrid(columns=cols, rows=rows, id="button_grid")

        self.update_access_buttons(grid=grid)

        yield Header(icon="(?)")
        yield grid

        with Horizontal(classes="bottom-hero"):
            yield Button("Fetch", classes="btn-fetch", id="permissions_fetch")
            yield Button("Submit", classes="btn-submit", id="permissions_submit")

    def find_access_value(self, col: int, row: int) -> Literal["NO_ACCESS", "READ_ONLY", "MODIFY"]:
        """Determine the value for a specific cell."""
        group = self.app.active_groups[col]
        column = self.app.active_table["metadata_detail"]["columns"][row]

        if self.app.active_table_security is None:
            return "NO_ACCESS"

        for access_column_info in self.app.active_table_security:
            for access_column_details in access_column_info["metadata_permission_details"]:
                if "principal_permission_info" not in access_column_details:
                    return "NO_ACCESS"

                if access_column_details["metadata_id"] != column["header"]["id"]:
                    continue

                for permission_info in access_column_details["principal_permission_info"]:
                    for permission in permission_info["principal_permissions"]:
                        if permission["principal_id"] == group["id"]:
                            return permission["shared_permission"]

        return "NO_ACCESS"

    def update_access_buttons(self, grid: Optional[button_grid.ButtonGrid] = None) -> None:
        """Update the AccessButtonCell values."""
        if grid is None:
            grid = self.query_one("#button_grid")

        assert isinstance(grid, button_grid.ButtonGrid), "SecurityConfig.grid must be a ButtonGrid."

        with self.app.batch_update():
            for row_idx, row in enumerate(grid.cells):
                for col_idx, cell in enumerate(row):
                    permission = self.find_access_value(col=col_idx, row=row_idx)
                    cell.set_active_value(permission)

    @on(button_grid.AccessButtonCell.Pressed)
    def give_user_feedback_on_toggle(self, event: button_grid.AccessButtonCell.Pressed) -> None:
        """Handle cell button presses with enhanced information."""
        group = self.app.active_groups[event.cell.col]["metadata_header"]["displayName"]

        if event.cell.row == -1:
            column = "ALL COLUMNS"
        else:
            column = self.app.active_table["metadata_detail"]["columns"][event.cell.row]["header"]["name"]

        self.notify(f"Configured [b green]{group}[/] to {event.button.name} for [b green]{column}[/]")

    @on(Button.Pressed)
    def give_user_feedback_on_press(self, event: button_grid.Button.Pressed) -> None:
        """Handle cell button presses with enhanced information."""
        if event.control.id == "permissions_fetch":
            self.fetch_access()
            self.notify("Fetching permissions..", severity="warning")

        if event.control.id == "permissions_submit":
            self.submit_access()
            self.notify("Submitting permissions..", severity="warning")

    # DEV NOTE: @boonhapus, 2024/12/14
    # work(exclusive=true) means only one task can be running at a time. This is
    # combined with the unique group identifier such that only one of these can
    # running at a give time.
    #

    @work(group="security", exclusive=True)
    async def fetch_access(self) -> None:
        column_guids = {_["header"]["id"] for _ in self.app.active_table["metadata_detail"]["columns"]}

        access = await workflows.metadata.permissions(
            typed_guids={"LOGICAL_COLUMN": column_guids},
            compat_ts_version=self.app.compat_ts_version,
            http=self.app.http,
        )

        self.app.active_table_security = access
        self.update_access_buttons()

    @work(group="security", exclusive=True)
    async def submit_access(self) -> None:
        grid = self.query_one("#button_grid")

        access = {  # type: ignore
            "NO_ACCESS": {"guids": [], "principals": []},
            "READ_ONLY": {"guids": [], "principals": []},
            "MODIFY": {"guids": [], "principals": []},
        }

        for row_idx, row in enumerate(grid.cells):
            for col_idx, cell in enumerate(row):
                column = self.app.active_table["metadata_detail"]["columns"][row_idx]
                group = self.app.active_groups[col_idx]

                access[cell.value]["guids"].append(column["header"]["id"])
                access[cell.value]["principals"].append(group["metadata_id"])

        coros = []

        for share_mode, options in access.items():
            if not options["guids"] or not options["principals"]:
                continue
            coros.append(
                self.app.http.security_metadata_share(
                    guids=[],
                    metadata=[{"type": "LOGICAL_COLUMN", "identifier": _} for _ in options["guids"]],
                    principals=options["principals"],
                    share_mode=share_mode,
                )
            )

        responses = await asyncio.gather(*coros)

        for share_mode, r in zip(access.keys(), responses):
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError:
                log.debug(r.text)
                self.notify(
                    f"Failed to set '{share_mode}', see logs for details..",
                    title="ThoughtSpot API Error",
                    severity="error",
                )
