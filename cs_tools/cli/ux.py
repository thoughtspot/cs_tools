from typing import Optional, Callable, List, Any
import contextlib
import logging
import sys

from rich.console import Console
import typer
import click

from cs_tools.cli.types import SyncerProtocolType
from cs_tools.const import GH_SYNCER

log = logging.getLogger(__name__)
rich_console = Console()
WARNING_BETA = "\n\n[bold yellow]USE AT YOUR OWN RISK![/] " "This tool is currently in beta."
WARNING_PRIVATE = (
    "\n\n[bold yellow]USE AT YOUR OWN RISK![/] "
    "This tool utilized private / internal API calls. These API calls are not "
    "[b]gauranteed[/] to be stable across ThoughtSpot version upgrades."
)


class CSToolsCommand(typer.core.TyperCommand):
    """CSTools Commands can have dependencies."""

    def __init__(self, **passthru):
        # We need these to forward options to the dependencies
        ctx_settings = passthru.pop("context_settings") or {}
        ctx_settings["allow_extra_args"] = True
        ctx_settings["ignore_unknown_options"] = True
        super().__init__(**passthru, context_settings=ctx_settings)
        self.dependencies: Callable[[click.Context], Any] = getattr(self.callback, "__cs_tools_dependencies__", [])

    def invoke(self, ctx: typer.Context) -> Any:
        """Hi-jack command execution to fire off dependencies."""
        with contextlib.ExitStack() as stack:
            for dependency in self.dependencies:
                stack.enter_context(dependency(ctx))

            r = ctx.invoke(self.callback, **ctx.params)

        return r

    def _augment_help_text(self, ctx: typer.Context, *, seen_params: List[click.Parameter]) -> List[click.Parameter]:
        """
        Inject Dependency parameters and help text.

        This action is performed for the --help commands only.
        """
        # no help command was sent, pass back what we saw..
        if not set(sys.argv[1:]).intersection(ctx.help_option_names):
            return seen_params

        # inject dependency's Parameters
        for dependency in self.dependencies:
            seen_params.extend([p for p in dependency.parameters if p not in seen_params])

        # add syncer documentation page help text
        if any(isinstance(p.type, SyncerProtocolType) for p in seen_params):
            syncer = f" :floppy_disk: [cyan][link={GH_SYNCER}]How do I use a Syncer?[/][/]"

            if self.epilog is None:
                self.epilog = ""

            if syncer not in self.epilog:
                self.epilog += syncer

        return seen_params

    def get_params(self, ctx: typer.Context) -> List[click.Parameter]:
        """Hi-jack for dependency help-text augmentations."""
        rv = super().get_params(ctx)
        rv = self._augment_help_text(ctx, seen_params=rv)
        return rv


class CSToolsGroup(typer.core.TyperGroup):
    """CSTools Groups should always recurse, and use CSToolsCommand."""
    command_class = CSToolsCommand
    group_class = type

    def list_commands(self, ctx: typer.Context) -> List[str]:  # noqa: ARG002
        """Override so we don't sort alphabetically."""
        return list(self.commands)


class CSToolsApp(typer.Typer):
    def __init__(self, **passthru):
        # We need to enforce these options for all Apps
        passthru["cls"] = CSToolsGroup
        passthru["rich_markup_mode"] = "rich"
        passthru["no_args_is_help"] = True
        super().__init__(**passthru)

    def command(
        self,
        name: Optional[str] = None,
        *,
        dependencies: Optional[List[Callable]] = None,
        # better typer defaults
        cls: Optional[CSToolsCommand] = CSToolsCommand,
        no_args_is_help: bool = True,
        **passthru,
    ):
        """Hi-jack to store dependencies."""
        def decorator(f: Callable):
            if not hasattr(f, "__cs_tools_dependencies__"):
                f.__cs_tools_dependencies__ = []

            if dependencies is not None:
                f.__cs_tools_dependencies__.extend(dependencies)

            info = typer.models.CommandInfo(name=name, cls=cls, callback=f, no_args_is_help=no_args_is_help, **passthru)
            self.registered_commands.append(info)
            return f

        return decorator
