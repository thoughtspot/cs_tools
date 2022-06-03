import importlib
import pathlib
import types

from pydantic.dataclasses import dataclass
import typer

from cs_tools.const import PACKAGE_DIR


@dataclass
class CSTool:
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
    docs_base_path: pathlib.Path = PACKAGE_DIR / 'docs' / 'cs-tools'

    @property
    def app(self) -> typer.Typer:
        """
        Access a tool's underlying typer app.
        """
        return self.lib.app

    @property
    def lib(self) -> types.ModuleType:
        """
        The python code which represents a tool.

        Currently, all tools must reside within the library, under the path
        cs_tools/cli/tools.. but we could expand this to customer created tools
        in the future.
        """
        if not hasattr(self, '_lib'):
            import_path = f'cs_tools.cli.tools.{self.directory.name}'
            self._lib = importlib.import_module(import_path)

        return self._lib

    @property
    def name(self) -> str:
        """
        Clean up and expose the tool's name.
        """
        to_trim = {
            'example': len(''),
            'beta': len('__b_'),
            'private': len('_'),
            'public': len(''),
        }

        n = to_trim[self.privacy]
        return self.directory.stem[n:]

    @property
    def privacy(self) -> str:
        """
        Determines the privacy level of a cs_tool.

        One of..
            example - a template tool
            beta - an unreleased tool
            private - a released tool which uses internal APIs
            public - a released tool which uses no internal APIs
            unknown - a catch-all for invalid tools

        Only public tools show up in the default cli help text. Other classes
        of tools may be shown with additional undocumented flags.
        """
        if self.directory.stem == '__example_app__':
            return 'example'

        if self.directory.stem.startswith('__b_'):
            return 'beta'

        if self.directory.stem.startswith('__'):
            return 'unknown'

        if self.directory.stem.startswith('_'):
            return 'private'

        if not self.directory.stem.startswith('_'):
            return 'public'

        return 'unknown'

    @property
    def version(self) -> str:
        """
        Show an app's version.
        """
        return self.lib.__version__

    def __repr__(self) -> str:
        return f'<{self.privacy.title()}Tool: {self.name}>'
