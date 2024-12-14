# ruff: noqa: RUF012
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Static


class SecuritySplash(Screen):
    DEFAULT_CSS = """
    SecuritySplash {
        # Center everything on screen.
        align: center middle;
    }

    .hero {
        # Give the HERO section a callout.
        background: $panel;

        # Center everything in middle of the callout.
        content-align: center middle;
        height: auto;
        width: 100%;

        # Give some negative space around.
        padding: 2 3 3 3;

        Static {
            # Align everything in the center.
            content-align: center middle;

            # Give the text some space between.
            margin: 1;
        }
        
        .buttons {
            # Ensure the buttons go side-by-side.
            layout: horizontal;

            # Center the buttons within the container.
            align-horizontal: center;
            height: auto;

            Button {
                # Give the buttons some space between.
                margin: 0 4;

                # Oh my God Becky.. don't be one of those rap guys' girlfriends.
                width: 45%;
            }
        }
    }
    """
    BINDINGS = [
        ("p", "app.switch_mode('home')", "Proceed"),
        ("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Render the HomeScreen."""
        with Container(classes="hero"):
            yield Static("🔒")
            yield Static("Security Screen")
            yield Static("If you can't see the lock icon above, quit and run in Web mode.")

            with Container(classes="buttons"):
                yield Button("Proceed", variant="success", action="app.switch_mode('home')")
                yield Button("Quit", variant="error", action="app.quit")
