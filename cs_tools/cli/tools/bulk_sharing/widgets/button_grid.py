from __future__ import annotations

from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal
from textual.message import Message
from textual.widgets import Button, Static


class AccessButtonCell(Horizontal):
    DEFAULT_CSS = """
    AccessButtonCell {
        align: center middle;

        .btn-access {
            min-width: 3;
            width: 3;
        
            &.inactive {
                opacity: 0.5;
            }
            
            &:hover {
                opacity: 0.9;
            }
            
            &.NO_ACCESS {
                # RED
                background: hsl(347, 99%, 64%);  # rgb(254, 72, 112) // #fe4870
            }
            
            &.READ_ONLY {
                # BLUE
                background: hsl(216, 96%, 50%);  # rgb(5, 103, 250) // #0567fa
            }
            
            &.MODIFY {
                # GREEN
                background: hsl(135, 42%, 50%);  # rgb(74, 181, 101) // #4ab565
            }
        }
    }
    """

    class Pressed(Message):
        """Event sent when a `Button` is pressed and there is no Button action."""

        def __init__(self, cell: AccessButtonCell, button: Button) -> None:
            super().__init__()
            self.cell = cell
            self.button = button

    def __init__(self, *, value: str | None, col: int, row: int, **widget_options) -> None:
        super().__init__(**widget_options)
        self.value = value
        self.col = col
        self.row = row
        self._buttons = {
            "NO_ACCESS": Button("X", name="NO_ACCESS", classes="btn-access NO_ACCESS inactive"),
            "READ_ONLY": Button("R", name="READ_ONLY", classes="btn-access READ_ONLY inactive"),
            "MODIFY": Button("M", name="MODIFY", classes="btn-access MODIFY inactive"),
        }

        if value is None:
            self.add_class("btn-access--header")

    def compose(self) -> ComposeResult:
        if not self.has_class("btn-access--header"):
            self.set_active_value(self.value)

        for _, button in self._buttons.items():
            yield button

    @property
    def active(self) -> Button:
        """Get the active button from the tri-button."""
        return self._buttons[self.value]

    def set_active_value(self, value: str) -> None:
        """Set the active button from the tri-button."""
        self.active.add_class("inactive")
        self.value = value
        self.active.remove_class("inactive")

    @on(Button.Pressed)
    async def handle_press(self, event: Button.Pressed) -> None:
        if not self.has_class("btn-access--header"):
            async with self.batch():
                assert event.button.name is not None, "Buttons should have a name."
                self.set_active_value(event.button.name)
                event.stop()

        self.post_message(AccessButtonCell.Pressed(cell=self, button=event.button))


class ButtonGrid(Grid):
    DEFAULT_CSS = """
    ButtonGrid {
        align: center middle;
        padding: 1 0 1 0;

        # ALLOW THE GRID TO SCROLL IF OVERFLOWN
        overflow: scroll;
        height: 100%;
        min-height: 20;
        max-height: 90vh;

        # HEIGHT OF THE ROWS
        grid-rows: 1;

        # WIDTH OF THE COLUMNS
        grid-columns: 1fr;

        # SPACE BETWEEN THE COLUMNS
        grid-gutter: 1 0;

        # CENTER THE CONTENT IN THE TOOLTIP
        .tooltip {
            content-align: right middle;
            height: 1;
            color: gray;
        }

        # RIGHT-ALIGN THE ROW HEADER
        .btn-grid--row-header {
            content-align: right middle;
            height: 1;
        }

        # CENTER-ALIGN THE COL HEADER
        .btn-grid--col-header {
            text-align: center;
        }
    }
    """

    def __init__(self, columns: list[str], rows: list[str], **widget_options) -> None:
        super().__init__(**widget_options)
        self.columns = columns
        self.rows = rows

        # style: { grid-size: rows columns; }
        self.styles.grid_size_columns = len(columns) + 1
        self.styles.grid_size_rows = len(rows) + 1

        # RowArray<ColumnArray<Cell>
        self.cells: list[list[AccessButtonCell]] = [
            [AccessButtonCell(value="NO_ACCESS", col=col_idx, row=row_idx) for col_idx, _ in enumerate(columns)]
            for row_idx, _ in enumerate(rows)
        ]

    def compose(self) -> ComposeResult:
        yield Static("")

        # BUILD THE HEADER ROW
        for col in self.columns:
            yield Static(col, classes="btn-grid--col-header").with_tooltip(col)

        yield Static("(?)", classes="tooltip").with_tooltip(
            "[#fe4870]No Access[/] | [#0567fa]Can View[/] | [#4ab565]Can Edit[/]"
            f"\n\n=== INFO ==="
            f"\n{len(self.rows):,} columns in table"
        )

        # BUILD THE BUTTON CONTROLLER ROW
        for col_idx, _ in enumerate(self.columns):
            yield AccessButtonCell(value=None, col=col_idx, row=-1)

        # BUILD THE CELLS
        for _row_idx, row in enumerate(self.cells):
            yield Static(self.rows[_row_idx], classes="btn-grid--row-header").with_tooltip(self.rows[_row_idx])

            for _col_idx, cell in enumerate(row):
                yield cell

    def get_cell(self, col: int, row: int) -> AccessButtonCell:
        """ "Get the cell at the specified position."""
        return self.cells[row][col]

    def set_cell(self, col: int, row: int, value: Any = None) -> None:
        """Set the value of a cell at the specified position."""
        try:
            cell = self.get_cell(col, row)
        except IndexError:
            self.notify(f"No cell at: {col}, {row}", title="Error", severity="error")
        else:
            cell.value = value

    @on(AccessButtonCell.Pressed)
    async def broadcast_column_header_button_press_to_cells(self, event: AccessButtonCell.Pressed) -> None:
        assert event.button.name is not None, "Buttons should have a name."

        if _is_header_button := event.cell.has_class("btn-access--header"):
            async with self.batch():
                for row_idx, _ in enumerate(self.rows):
                    cell = self.get_cell(col=event.cell.col, row=row_idx)
                    cell.set_active_value(event.button.name)
