from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import importlib
import pathlib
import sys

from typer.testing import CliRunner, Result

from cs_tools.cli.ux import WARNING_BETA, WARNING_PRIVATE
from cs_tools.const import GH_ISSUES, PACKAGE_DIR
from cs_tools.datastructures import _GlobalModel

if TYPE_CHECKING:
    import types

    import typer


class CSTool(_GlobalModel):
    """
    Represent a tool which a user can interact with.

    Tools must take AT LEAST the following form..

    cs_tools/
    ├─ cs_tools/
    │  └─ cli/
    │     └─ tools/
    │        └─ < tool-name/ >
    │           ├─ __init__.py
    │           ├─ _version.py
    │           ├─ ...
    │           └─ app.py
    └─ docs/
       └─ cs-tools/
          └─ < tool-name/ >
             ├─ ...
             └─ README.md

    In that tools will exist in the cs_tools.cli.tools directory, and have an
    associated documentation page.
    """

    directory: pathlib.Path
    docs_base_path: pathlib.Path = PACKAGE_DIR / "docs" / "cs-tools"

    def __init__(self, **data):
        super().__init__(**data)

        if self.privacy == "unknown":
            return

        self.app.rich_help_panel = "Available Tools"

        # Augment CLI Info
        if self.privacy == "beta":
            self.app.rich_help_panel = f"[BETA Tools] [green]give feedback :point_right: [cyan][link={GH_ISSUES}]GitHub"
            self.app.info.help += WARNING_BETA

        if self.privacy == "private":
            self.app.rich_help_panel = "[PRIVATE Tools] :yellow_circle: [yellow]uses internal APIs, use with caution!"
            self.app.info.help += WARNING_PRIVATE

        self.app.info.epilog = f":bookmark: v{self.version} :scroll: [cyan][link={self.docs_url}]Documentation"

    @property
    def privacy(self) -> str:
        """
        Determines the privacy level of a cs_tool.

        One of..
            beta - an unreleased tool
            private - a released tool which uses internal APIs
            public - a released tool which uses no internal APIs
            unknown - a catch-all for invalid tools

        Only public tools show up in the default cli help text. Other classes
        of tools may be shown with additional undocumented flags.
        """
        if self.directory.stem.startswith("__b_"):
            return "beta"

        if self.directory.stem.startswith("__"):
            return "unknown"

        if self.directory.stem.startswith("_"):
            return "private"

        if not self.directory.stem.startswith("_"):
            return "public"

        return "unknown"

    @property
    def name(self) -> str:
        """
        Clean up and expose the tool's name.
        """
        to_trim = {"beta": len("__b_"), "private": len("_"), "public": len("")}
        n = to_trim.get(self.privacy, 0)
        return self.directory.stem[n:]

    @property
    def lib(self) -> types.ModuleType:
        """
        The python code which represents a tool.

        Currently, all tools must reside within the library, under the path
        cs_tools/cli/tools.. but we could expand this to customer created tools
        in the future.
        """
        if not hasattr(self, "_lib"):
            import_path = f"cs_tools.cli.tools.{self.directory.name}"
            self._lib = sys.modules[import_path] = importlib.import_module(import_path)

        return self._lib

    @property
    def app(self) -> typer.Typer:
        """
        Access a tool's underlying typer app.
        """
        return self.lib.app

    @property
    def docs_url(self) -> str:
        """
        References the documentation page.
        """
        return f"https://thoughtspot.github.io/cs_tools/cs-tools/{self.name}/"

    @property
    def version(self) -> str:
        """
        Show an app's version.
        """
        return self.lib.__version__

    def invoke(self, command: str, args: Optional[list[str]] = None) -> Result:
        """
        Run a command in this tool's app.
        """
        if args is None:
            args = []

        from cs_tools import utils

        self.lib.app.info.context_settings = {"obj": utils.State()}

        runner = CliRunner()
        result = runner.invoke(app=self.lib.app, args=[command, *args], catch_exceptions=False)
        return result

    def __repr__(self) -> str:
        return f"<{self.privacy.title()}Tool: {self.name}>"
