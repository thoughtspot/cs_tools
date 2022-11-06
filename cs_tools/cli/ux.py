from typing import Any, Callable, List, Optional, Tuple
import contextlib
import logging
import sys

from click.exceptions import UsageError
from rich.console import Console
from rich.markup import escape
from click.core import iter_params_for_processing
import typer
import click

from cs_tools.const import CONSOLE_THEME, GH_SYNCER
from cs_tools import __version__


log = logging.getLogger(__name__)
console = Console(theme=CONSOLE_THEME)
WARNING_BETA = (
    "\n\n[bold yellow]USE AT YOUR OWN RISK![/] "
    "This tool is currently in beta."
)
WARNING_PRIVATE = (
    "\n\n[bold yellow]USE AT YOUR OWN RISK![/] "
    "This tool utilized private / internal API calls. These API calls are not "
    "[b]gauranteed[/] to be stable across ThoughtSpot version upgrades."
)


class CSToolsCommand(typer.core.TyperCommand):

    def __init__(self, **passthru):
        ctx_settings = passthru.pop("context_settings") or {}
        # we need these to forward options to the dependencies
        ctx_settings["allow_extra_args"] = True
        ctx_settings["ignore_unknown_options"] = True
        super().__init__(**passthru, context_settings=ctx_settings)

    def invoke(self, ctx: typer.Context) -> Any:
        with contextlib.ExitStack() as stack:
            if hasattr(self.callback, "dependencies"):
                [stack.enter_context(dep(ctx)) for dep in self.callback.dependencies]
    
            r = ctx.invoke(self.callback, **ctx.params)

        return r

    #

    def augment_help_text(self, ctx: click.Context, *, seen_params: List[click.Parameter]) -> List[click.Parameter]:
        """
        Inject Dependency parameters and help text.

        This action is performed for the --help commands only.
        """
        os_args = sys.argv[1:]

        # if we're issuing the HELP command, inject dependency's Parameters
        if not set(os_args).intersection(ctx.help_option_names):
            return seen_params

        for dependency in getattr(self.callback, "dependencies", []):
            seen_params.extend([p for p in dependency.parameters if p not in seen_params])

        if any("protocol" in str(p.metavar) for p in seen_params):
            syncer = f" :floppy_disk: [cyan][link={GH_SYNCER}]How do I use a Syncer?"

            if self.epilog is None:
                self.epilog = ""

            if syncer not in self.epilog:
                self.epilog += syncer

        return seen_params

    def get_params(self, ctx: click.Context) -> List[click.Parameter]:
        """
        Override for augmentations.
        """
        rv = super().get_params(ctx)
        rv = self.augment_help_text(ctx, seen_params=rv)
        return rv


class CSToolsApp(typer.Typer):

    def __init__(self, **passthru):
        passthru["rich_markup_mode"] = "rich"
        super().__init__(**passthru)

    def command(
        self,
        name: Optional[str] = None,
        *,
        dependencies: Optional[List[Callable]] = None,
        # typer kwargs
        cls: Optional[CSToolsCommand] = CSToolsCommand,
        **passthru
    ):
        """
        Override to inject dependencies.
        """
        if dependencies is None:
            dependencies = []

        def decorator(f: Callable):
            if not hasattr(f, "dependencies"):
                f.dependencies = []

            f.dependencies.extend(dependencies)
            info = typer.models.CommandInfo(name=name, cls=cls, callback=f, **passthru)
            self.registered_commands.append(info)
            return f

        return decorator


class CSToolsGroup(typer.core.TyperGroup):
    command_class = CSToolsCommand
    group_class = type

    def list_commands(self, ctx: click.Context) -> List[str]:
        """
        Override so we don't sort alphabetically
        """
        return list(self.commands)
