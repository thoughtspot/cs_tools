# ruff: noqa: RUF012
from __future__ import annotations

from typing import Any
import json
import logging

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Footer, Pretty, Static, TextArea

from cs_tools import datastructures, types
from cs_tools.api import workflows
from cs_tools.api.client import RESTAPIClient
from cs_tools.cli import ux

log = logging.getLogger(__name__)


class ResultsBox(Widget):
    """A widget for displaying query results."""

    widget_type: reactive[str] = reactive("static")

    def __init__(self, data: Any, **widget_options):
        super().__init__(**widget_options)
        self._static_widget = Static(data)
        self._pretty_widget = Pretty("")
        self._dtable_widget = DataTable(zebra_stripes=True)
        self.data: Any = data

    def update(self, data: Any, *, as_data_table=False) -> None:
        """Update the widget with new data."""
        self.data = data

        if as_data_table:
            self._dtable_widget.clear(columns=True)
            self._dtable_widget.add_columns(*data[0].keys())
            self._dtable_widget.add_rows(row.values() for row in data)
            self.widget_type = "table"

        elif all(isinstance(r, str) for r in data):
            self._static_widget.update(data)
            self.widget_type = "static"

        else:
            self._pretty_widget.update(data)
            self.widget_type = "pretty"

    def watch_widget_type(self, new_widget_type: str) -> None:
        """Watch for changes to widget_type and trigger remount"""
        if self._pretty_widget in self.children:
            self._pretty_widget.remove()

        if self._static_widget in self.children:
            self._static_widget.remove()

        if self._dtable_widget in self.children:
            self._dtable_widget.remove()

        # Mount new widget
        if new_widget_type == "pretty":
            self.mount(self._pretty_widget)
        elif new_widget_type == "table":
            self.mount(self._dtable_widget)
        else:
            self.mount(self._static_widget)

    def compose(self) -> ComposeResult:
        """Render the widget."""
        if self.widget_type == "table":
            yield self._dtable_widget
        if self.widget_type == "static":
            yield self._static_widget
        else:
            yield self._pretty_widget


class Editor(Screen):
    """A TUI application for executing SQL queries."""

    DEFAULT_CSS = """
    Editor {
        layout: grid;
        grid-size: 3;
        grid-rows: 3 1fr 9 2fr;
    }

    #editor {
        column-span: 3;
    }

    #falcon-context {
        column-span: 3;
        text-align: center;
        color: 60% gray;
        min-height: 3;
        padding: 1 0 0 0;
    }

    #falcon-context.unsafe {
        color: 60% #fe4870;  # ux._TS_PURPLE
    }

    #controls-container {
        column-span: 3;

        layout: grid;
        grid-size: 3;

        align: center middle;

        Button {
            width: 1fr;
            margin: 0 5;
        }
        
        Static {
            text-align: center;
            color: 40% gray;
        }
    }

    #results-container {
        column-span: 3;
        row-span: 1;
        border: #8d63f5;  # ux._TS_PURPLE

        Static {
            padding: 1 2;
        }
    }
    """

    BINDINGS = [
        Binding("ctrl+d", "clear_query", "Clear Query", show=False, priority=True),
        Binding("ctrl+j", "execute_query", "Execute Query", show=False),
        Binding("ctrl+g", "copy_result", "Copy Result", show=False),
        Binding("ctrl+q", "quit", "Quit", priority=True),
        # Binding("ctrl+h", "show_help", "Help"),
    ]

    TITLE = "Remote TQL"

    def compose(self) -> ComposeResult:
        yield Static(self.make_context(), id="falcon-context", classes="unsafe" if self.app.admin_mode else None)
        yield TextArea.code_editor(id="editor")

        with Container(id="controls-container"):
            yield Button("Clear", name="clear")
            yield Button("Execute", name="execute")
            yield Button("Copy Data", name="copy")
            yield Static("ctrl + d")
            yield Static("ctrl + enter")
            yield Static("ctrl + g")

        with Container(id="results-container"):
            yield ResultsBox("Waiting for query..", id="result")

        yield Footer(show_command_palette=False)

    def make_context(self) -> str:
        """Write the context string."""
        context = self.app.current_falcon_ctx["schema"]

        if database := self.app.current_falcon_ctx.get("database", ""):
            context = f"{database}.{context}"

        return f"Falcon Context: {context}"

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.name == "clear":
            self.action_clear_query()

        if event.button.name == "execute":
            self.action_execute_query()

        if event.button.name == "copy":
            self.action_copy_result()

    @work(name="clear", exclusive=True)
    async def action_clear_query(self) -> None:
        """Clears the editor to start a new query."""
        editor = self.query_one("#editor")
        assert isinstance(editor, TextArea), "#editor is not a TextArea"
        editor.text = ""

    @work(name="copy", exclusive=True)
    async def action_copy_result(self) -> None:
        """Copies the results to the clipboard."""
        result = self.query_one("#result")
        assert isinstance(result, ResultsBox), "#result is not a ResultsBox"

        text = result.data

        if result.widget_type != "static":
            text = json.dumps(result.data, indent=4, default=str)

        self.app.copy_to_clipboard(text)
        self.notify("Copied results to your clipboard!")

    @work(name="execute", exclusive=True)
    async def action_execute_query(self) -> None:
        """Execute the current SQL query and display results."""
        editor = self.query_one("#editor")
        r_wrap = self.query_one("#results-container")
        result = self.query_one("#result")

        assert isinstance(editor, TextArea), "#editor is not a TextArea"
        assert isinstance(result, ResultsBox), "#result is not a ResultsBox"

        try:
            result.loading = True

            d = await workflows.tql.query(
                editor.text,
                falcon_context=self.app.current_falcon_ctx,
                record_offset=0,
                record_size=50,
                allow_unsafe=self.app.admin_mode,
                http=self.app.http,
            )

        except Exception as e:
            r_wrap.styles.border = ("solid", ux._TS_RED)
            result.update(f"Error executing query: {e}")
            self.notify(f"{e}", title="Something went wrong!", severity="error")
            raise

        else:
            self.app.current_falcon_ctx = d["curr_falcon_context"]
            self.query_one("#falcon-context").update(self.make_context())

            if d["data"]:
                content = d["data"]
            elif not self.app.admin_mode:
                content = d["message"]["content"]
            else:
                content = d["original"]

            result.update(content, as_data_table=bool(d["data"]))

            severity_map = {
                "DEBUG": ("information", ux._TS_PURPLE),
                "INFO": ("information", ux._TS_GREEN),
                "WARNING": ("warning", ux._TS_YELLOW),
                "ERROR": ("error", ux._TS_RED),
            }

            severity, color = severity_map[d["message"]["severity"]]

            r_wrap.styles.border = ("solid", color)

            if d["message"]["content"]:
                self.notify(d["message"]["content"].strip(), severity=severity)

        finally:
            result.loading = False


class RemoteTQLApp(App):
    """Interact with a remote Falcon database on your local machine."""

    MODES = {
        "editor": Editor,
    }

    def __init__(self, sess_ctx: datastructures.SessionContext, http: RESTAPIClient, admin_mode: bool = False):
        super().__init__()
        self.admin_mode = admin_mode
        self.sess_ctx = sess_ctx
        self.http = http
        self.current_falcon_ctx = {"schema": "falcon_default_schema", "server_schema_version": -1}

    def on_mount(self) -> None:
        self.switch_mode("editor")


if __name__ == "__main__":
    # ================================================================//
    #
    # DO NOT EDIT!!! THIS IS NEEDED FOR app.py --mode web TO WORK.
    #
    import argparse

    from cs_tools import errors
    from cs_tools.settings import CSToolsConfig
    from cs_tools.thoughtspot import ThoughtSpot

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Configuration file identifier", default=None)
    parser.add_argument("--admin", help="Enable admin mode", action=argparse.BooleanOptionalAction)
    option = parser.parse_args()

    cfg = CSToolsConfig.from_name(name=option.config)
    tse = ThoughtSpot(config=cfg, auto_login=True)
    #
    # ================================================================//
    if not tse.session_context.user.is_data_manager:
        raise errors.InsufficientPrivileges(
            user=tse.session_context.user,
            service="Remote TQL",
            required_privileges=[types.GroupPrivilege.can_manage_data],
        )

    app = RemoteTQLApp(sess_ctx=tse.session_context, admin_mode=option.admin, http=tse.api)
    app.run()
