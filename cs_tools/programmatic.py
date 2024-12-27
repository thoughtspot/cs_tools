from __future__ import annotations

import functools as ft
import importlib.util
import pathlib
import shlex
import sys
import types

from typer.testing import CliRunner, Result
import pydantic

from cs_tools import cli, utils
from cs_tools.datastructures import _GlobalModel
from cs_tools.errors import CSToolsError


class CSToolInfo(_GlobalModel):
    """Represents all the relevant information about a CS Tool."""

    directory: pathlib.Path

    @pydantic.computed_field
    @property
    def privacy(self) -> str:
        """Determine the visibility of the tool in normal CLI operations."""
        if not self.directory.is_relative_to(utils.get_package_directory("cs_tools")):
            return "custom"

        if self.directory.stem.startswith("__b_"):
            return "beta"

        if self.directory.stem.startswith("_"):
            return "private"

        return "public"

    @pydantic.computed_field
    @property
    def name(self) -> str:
        """Determine the name of the tool."""
        if self.directory.stem.startswith("__b_"):
            return self.directory.stem[len("__b_") :]

        if self.directory.stem.startswith("_"):
            return self.directory.stem[len("_") :]

        return self.directory.stem

    @classmethod
    def fetch_builtin(cls, name: str) -> CSToolInfo:
        """Fetch a built-in tool by name."""
        CS_TOOLS_PKG_DIR = utils.get_package_directory("cs_tools")

        tool_info = cls(directory=CS_TOOLS_PKG_DIR / "cli" / "tools" / name)

        try:
            _ = tool_info.app
        except ModuleNotFoundError:
            raise CSToolsError(f"Could not find tool {name}") from None

        return tool_info

    def import_module(self) -> types.ModuleType:
        """Import a Tool."""
        # DEV NOTE: @boonhapus, 2024/12/27
        # Probably a better way to do this is to use a dynamic loader instead, that way
        # tools can specify their own requirements and tools could be loaded from remote
        # if needed (ala uv), but meh.. there's all of like 5 people using this
        # interface today (and they're all internal-thoughtspot scripts).
        #
        # https://docs.python.org/3/library/importlib.html#importlib.abc.Loader
        #

        # PLACE OUR IMPORT PATH IN THE cs_tools.cli.tools NAMESPACE.
        namespace = "custom" if self.privacy == "custom" else "cli"
        module_name = f"cs_tools.{namespace}.tools.{self.name}"

        # CHECK IF THE MODULE IS ALREADY LOADED.
        if module_name in sys.modules:
            return sys.modules[module_name]

        # DYNAMICALLY IMPORT THE MODULE.
        spec = importlib.util.spec_from_file_location(
            name=self.name if self.privacy == "custom" else module_name,
            location=self.directory / "__init__.py",
        )

        try:
            assert spec is not None, f"Module could not be found at {self.directory}"
            assert spec.loader is not None, f"Module could not be found at {self.directory}"
        except AssertionError:
            raise ModuleNotFoundError(f"Module spec could not be built from {self.directory}") from None

        # CREATE THE MODULE.
        module = importlib.util.module_from_spec(spec)

        # TEMPORARILY ADD PARENT DIR TO PATH.
        if self.privacy == "custom":
            sys.path.insert(0, self.directory.parent.as_posix())

        # EXECUTE THE MODULE CODE.
        spec.loader.exec_module(module)

        # ADD IT TO sys.path (aka IMPORT IT).
        sys.modules[module_name] = module

        # TEMPORARILY ADD PARENT DIR TO PATH.
        if self.privacy == "custom":
            sys.path.remove(self.directory.parent.as_posix())

        return module

    @ft.cached_property
    def module(self) -> types.ModuleType:
        """Fetch the imported python module for this tool."""
        return self.import_module()

    @property
    def app(self) -> cli.ux.AsyncTyper:
        """Fetch the CLI app for this tool."""
        return self.module.app

    def invoke(self, *cli_args: str) -> Result:
        """Execute a command or subcommand on the tool."""
        # ENSURES CLI INPUT IS A LIST OF STRINGS.
        cli_args = shlex.split(" ".join(cli_args))  # type: ignore[assignment]

        return CliRunner().invoke(app=self.app, args=cli_args)
