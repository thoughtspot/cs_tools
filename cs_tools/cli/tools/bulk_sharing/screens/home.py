# ruff: noqa: RUF012
from __future__ import annotations

import logging

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, RadioButton, RadioSet, SelectionList
import httpx

from cs_tools import types
from cs_tools.api import workflows
from cs_tools.cli.tools.bulk_sharing import widgets

log = logging.getLogger(__name__)


class SecurityHome(Screen):
    DEFAULT_CSS = """
    SecurityHome {
        layout: grid;
        grid-size: 2;
    }

    .column {
        padding: 1;

        Label {
            # Align the first letter with the Input box.
            padding: 0 0 0 1;
            # Give a little gap at the bottom of the input label.
            margin: 0 0 1 0;
        }

        Input {
            # Align the T in "Type.." to the radio buttons.
            padding: 0 2;

            # Give a little gap at the bottom of the input box.
            margin: 0 0 1 0;
        }

        RadioSet {
            width: 100%;
        }
    }

    #bottom-hero {
        dock: bottom;

        # Place the contents in the center of the hero section.
        align-horizontal: center;
        height: auto;

        Button {
            # Oh my God Becky.. don't be one of those rap guys' girlfriends.
            width: 45%;

            # Float the button a little bit from the bottom of the screen.
            margin: 0 0 2 0;
        }
    }
    """
    BINDINGS = [
        ("enter", "navigate_to_security_screen", "Submit"),
        ("r", "reset_selections", "Reset"),
    ]

    TITLE = "Bulk Sharing Configuration"

    tables: reactive[list[types.APIResult]] = reactive(list, recompose=True)
    groups: reactive[list[types.APIResult]] = reactive(list, recompose=True)

    def _make_table_selection_text(self, table_info: types.APIResult) -> str:
        type_mapping = {
            "WORKSHEET": "[b yellow]W[/]",
            "MODEL": "[b yellow]M[/]",
            "AGGR_WORKSHEET": "[b purple]V[/]",
            "SQL_VIEW": "[b purple]S[/]",
            "USER_DEFINED": "[b green]U[/]",
            "ONE_TO_ONE_LOGICAL": "[b green]T[/]",
        }
        name = table_info["metadata_name"]
        type = type_mapping.get(table_info["metadata_header"]["type"])
        return f"{type} [dim]|[/] {name}"

    def _make_group_selection_text(self, group_info: types.APIResult) -> str:
        name = group_info["metadata_header"]["displayName"]
        style = "[b yellow dim]" if group_info["metadata_detail"]["visibility"] == "NON_SHARABLE" else ""
        return f"{style}{name}"

    def compose(self) -> ComposeResult:
        """Render the SecurityHome."""
        DEFAULT_TABLES = [{"metadata_header": {"type": "MODEL"}, "metadata_name": "(Sample) Retail Apparel"}]
        DEFAULT_GROUPS = [
            {"metadata_header": {"displayName": "All Group"}, "metadata_detail": {"visibility": "SHARABLE"}}
        ]

        yield Header(icon="(?)")

        tables = self.tables if self.tables else DEFAULT_TABLES
        groups = self.groups if self.groups else DEFAULT_GROUPS

        with Container(classes="column"):
            yield Label("Table Selector")
            yield widgets.search_bar.DebouncedInput(
                delay=0.5, type="text", placeholder="Type a Table name..", id="table_search"
            )
            yield RadioSet(
                *(self._make_table_selection_text(_) for _ in tables), id="table_options", disabled=not self.tables
            )

        with Container(classes="column"):
            yield Label("Group Selector")
            yield widgets.search_bar.DebouncedInput(
                delay=0.5, type="text", placeholder="Type a Group name..", id="group_search"
            )
            yield SelectionList(
                *((self._make_group_selection_text(_), idx) for idx, _ in enumerate(groups)),
                id="group_options",
                disabled=not self.groups,
            )

        with Container(id="bottom-hero"):
            yield Button("Fetch Security")

        yield Footer(show_command_palette=False)

    def action_reset_selections(self) -> None:
        """Reset the table and group selections."""
        with self.app.batch_update():
            self.tables.clear()
            self.mutate_reactive(SecurityHome.tables)

            self.groups.clear()
            self.mutate_reactive(SecurityHome.groups)

    @on(Button.Pressed)
    def action_navigate_to_security_screen(self, _: Button.Pressed = None) -> None:
        """Forward the typed value on to the data handler."""
        t_opts: RadioSet = self.query_one("#table_options")
        g_opts: SelectionList = self.query_one("#group_options")

        try:
            assert g_opts.selected != [], ""
            self.app.active_table = self.tables[t_opts.pressed_index]
            self.app.active_groups = [self.groups[pressed_idx] for pressed_idx in g_opts.selected]
        except AssertionError:
            self.notify("You must select groups first.", title="You're not ready yet!", severity="warning")
        except IndexError:
            self.notify("You must select a table first.", title="You're not ready yet!", severity="warning")
        else:
            self.app.switch_mode("security")

    @on(widgets.search_bar.DebouncedInput.Changed)
    def forward_typed_value_to_data_handler(self, event: Input.Changed) -> None:
        """Forward the typed value on to the data handler."""
        if event.control.id == "table_search":
            self.fetch_table_results(partial_name=event.value)

        if event.control.id == "group_search":
            self.fetch_group_results(partial_name=event.value)

    @on(RadioButton.Changed)
    def forward_selected_value_to_data_handler(self, event: RadioButton.Changed) -> None:
        """Forward the selected value on to the data handler."""
        if event.value:
            self.fetch_access_results(table_display_value=event.radio_button.label)

    @work(group="tables", exclusive=True)
    async def fetch_table_results(self, partial_name: str) -> None:
        try:
            options = self.query_one("#table_options")
            options.loading = True

            r = await self.app.http.metadata_search(
                guid="",
                metadata=[{"type": "LOGICAL_TABLE", "name_pattern": partial_name}],
                include_details=True,
                include_hidden_objects=True,
                record_size=-1,
            )

            r.raise_for_status()

        except httpx.HTTPStatusError:
            log.error(f"Could not fetch metadata/details for LOGICAL_TABLE contains '{partial_name}'")
            log.debug(r.text)
            self.notify(
                f"Couldn't fetch tables for '{partial_name}', see logs for details..",
                title="ThoughtSpot API Error",
                severity="error",
            )
            return

        except Exception as e:
            log.debug(f"Searching for LOGICAL_TABLE '{partial_name}' failed", exc_info=True)
            self.notify(f"{e}", title="Something went wrong!", severity="error")
            return

        else:
            if data := r.json():
                data = [_ for _ in data if _["metadata_header"]["type"] == "ONE_TO_ONE_LOGICAL"]
                self.tables = sorted(data, key=lambda x: x["metadata_header"]["modified"], reverse=True)
                self.mutate_reactive(SecurityHome.tables)
            else:
                self.notify(f"No tables found for '{partial_name}'", title="Did you make a typo?", severity="warning")

        finally:
            options.loading = False

    @work(group="groups", exclusive=True)
    async def fetch_group_results(self, partial_name: str) -> None:
        try:
            options = self.query_one("#group_options")
            options.loading = True

            r = await self.app.http.metadata_search(
                guid="",
                metadata=[{"type": "USER_GROUP", "name_pattern": partial_name}],
                include_details=True,
                record_size=-1,
            )

            r.raise_for_status()

        except httpx.HTTPStatusError:
            log.error(f"Could not fetch metadata/details for USER_GROUP contains '{partial_name}'")
            log.debug(r.text)
            self.notify(
                f"Couldn't fetch USER_GROUP for '{partial_name}', see logs for details..",
                title="ThoughtSpot API Error",
                severity="error",
            )
            return

        except Exception as e:
            log.debug(f"Searching for USER_GROUP '{partial_name}' failed", exc_info=True)
            self.notify(f"{e}", title="Something went wrong!", severity="error")
            return

        else:
            if data := r.json():
                self.groups.extend(data)
                self.groups.sort(key=lambda x: x["metadata_header"]["displayName"])
                self.mutate_reactive(SecurityHome.groups)
            else:
                self.notify(f"No groups found for '{partial_name}'", title="Did you make a typo?", severity="warning")

        finally:
            options.loading = False

    @work(group="security", exclusive=True)
    async def fetch_access_results(self, table_display_value: str) -> None:
        _, _, table_name = table_display_value.partition(" | ")
        table = next(_ for _ in self.tables if _["metadata_name"] == table_name)
        column_guids = {_["header"]["id"] for _ in table["metadata_detail"]["columns"]}

        access = await workflows.metadata.permissions(
            typed_guids={"LOGICAL_COLUMN": column_guids},
            compat_ts_version=self.app.compat_ts_version,
            http=self.app.http,
        )

        self.app.active_table_security = access
