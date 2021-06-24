import importlib
import pathlib

import typer

from cs_tools.const import PACKAGE_DIR


class CSTool:
    """
    Represent a tool which a user can interact with.

    CS Tools all live under a tools/ subpackage, where the convention is
    that the tool's name is also the name of the sub-subpackage.

    NOTE:
      We don't yet do much with this class, but the pattern is quite
      useful if we wanted to expose tools to each other in a safe and
      composable manner.
    """
    def __init__(self, path: pathlib.Path):
        self.path = path
        self.lib = importlib.import_module(f'cs_tools.tools.{path.name}')

    @property
    def app(self) -> typer.Typer:
        """
        Access a tool's underlying typer app.
        """
        return self.lib.app

    @property
    def name(self) -> str:
        """
        Clean up and expose the tool's name.
        """
        if self.is_private and self.path.stem != '__example_app__':
            return self.path.stem[1:]

        return self.path.stem

    @property
    def version(self) -> str:
        """
        Show an app's version.
        """
        return self.lib.__version__

    @property
    def is_private(self) -> bool:
        """
        Mark the tool as private.

        Private tools will not show up in the default helptext. These
        tools may still be accessed by name, or be made visible through
        the use of an undocumented --private flag.
        """
        return self.path.stem.startswith('_')

    def __repr__(self) -> str:
        if self.is_private:
            pvt = 'Private'
        else:
            pvt = ''

        return f'<{pvt}Tool: {self.name}>'


def _gather_tools(app: typer.Typer):
    """
    Find and register all the available tools.
    """
    for path in (PACKAGE_DIR / 'tools').iterdir():
        if path.name.startswith('__') and path.name != '__example_app__':
            continue

        if path.is_dir():
            tool = CSTool(path)
            app.add_typer(tool.app, name=tool.name, hidden=tool.is_private)
