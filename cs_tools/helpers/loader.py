import importlib
import pathlib

import typer

from cs_tools.const import PACKAGE_DIR


class BSTool:
    """
    """

    def __init__(self, path: pathlib.Path):
        self.path = path
        self.lib = importlib.import_module(f'cs_tools.tools.{path.name}')

    @property
    def app(self):
        """
        """
        return self.lib.app

    @property
    def name(self):
        """
        """
        if self.is_private:
            return self.path.stem[1:]

        return self.path.stem

    @property
    def version(self):
        """
        """
        return self.lib.__version__

    @property
    def is_private(self) -> bool:
        """
        """
        return self.path.stem.startswith('_')

    def __repr__(self):
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
        if path.name.startswith('__'):
            continue

        if path.is_dir():
            tool = BSTool(path)
            app.add_typer(tool.app, name=tool.name, hidden=tool.is_private)
