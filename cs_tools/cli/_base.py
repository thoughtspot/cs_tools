from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import importlib
import pathlib
import shlex
import sys

from typer.testing import CliRunner, Result

from cs_tools import __project__
from cs_tools.datastructures import _GlobalModel
import cs_tools

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
    docs_base_path: pathlib.Path = pathlib.Path(cs_tools.__file__).parent.parent / "docs" / "cs-tools"

    def __init__(self, **data):
        super().__init__(**data)
        self._lib = self._import_module()

        if self.privacy == "unknown":
            return

        self.app.rich_help_panel = "Available Tools"

        if self.privacy == "beta":
            self.app.rich_help_panel = f"[BETA Tools] [green]feedback at [cyan][link={__project__.__help__}]GitHub"
            self.app.info.help += "\n\n[bold yellow]USE AT YOUR OWN RISK![/] This tool is currently in beta."

        self.app.info.epilog = f":bookmark: v{self.version} :scroll: [cyan][link={self.docs_url}]Documentation"

    def _import_module(self) -> types.ModuleType:
        import_path = f"cs_tools.cli.tools.{self.directory.name}"
        sys.modules[import_path] = importlib.import_module(import_path)
        return sys.modules[import_path]

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

        if not self.directory.stem.startswith("_"):
            return "public"

        return "unknown"

    @property
    def name(self) -> str:
        """Clean up and expose the tool's name."""
        to_trim = {"beta": len("__b_"), "private": len("_"), "public": len("")}
        n = to_trim.get(self.privacy, 0)
        return self.directory.stem[n:]

    @property
    def app(self) -> typer.Typer:
        """Access a tool's underlying typer app."""
        return self._lib.app

    @property
    def docs_url(self) -> str:
        """References the documentation page."""
        return f"https://thoughtspot.github.io/cs_tools/tools/{self.name}/"

    @property
    def version(self) -> str:
        """Show an app's version."""
        return self._lib.__version__

    def invoke(self, command: str, arguments: Optional[str] = None) -> Result:
        """
        Run a command in this tool's app.
        """
        if arguments is None:
            arguments = ""

        from cs_tools import utils

        self._lib.app.info.context_settings = {"obj": utils.GlobalState()}

        runner = CliRunner()
        result = runner.invoke(app=self._lib.app, args=[command, *shlex.split(arguments)], catch_exceptions=False)
        return result

    def __repr__(self) -> str:
        return f"<{self.privacy.title()}Tool: {self.name}>"
