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


class CSToolsArgumentInfo(typer.models.ArgumentInfo):
    """
    Override to add .custom_type , for implementing click.ParamType
    """
    def __init__(self, *a, custom_type: Any = None, **kw):
        self.custom_type = custom_type
        super().__init__(*a, **kw)


class CSToolsOptionInfo(typer.models.OptionInfo):
    """
    Override to add .custom_type , for implementing click.ParamType
    """
    def __init__(self, *a, custom_type: Any = None, **kw):
        self.custom_type = custom_type
        super().__init__(*a, **kw)


def CSToolsArgument(default, **passthru) -> typer.models.ArgumentInfo:
    """
    Typer does this with a function definition, even though they behave like classes.
    """
    passthru["show_default"] = passthru.get("show_default", default not in (..., None))
    return CSToolsArgumentInfo(default=default, **passthru)


def CSToolsOption(default, *param_decls, **passthru) -> typer.models.OptionInfo:
    """
    Typer does this with a function definition, even though they behave like classes.
    """
    passthru["show_default"] = passthru.get("show_default", default not in (..., None))
    return CSToolsOptionInfo(default=default, param_decls=param_decls, **passthru)


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
                for dependency in self.callback.dependencies:
                    log.debug(f"loading dependency: {dependency}")
                    stack.enter_context(dependency(ctx))

            log.debug(f"invoking {self.callback}")
            r = ctx.invoke(self.callback, **ctx.params)

        return r

    #

    def augment_help_text(self, ctx: typer.Context, *, seen_params: List[click.Parameter]) -> List[click.Parameter]:
        """
        Inject Dependency parameters and help text.

        This action is performed for the --help commands only.
        """
        # no help command was sent, pass back what we saw..
        if not set(sys.argv[1:]).intersection(ctx.help_option_names):
            return seen_params

        # inject dependency's Parameters
        for dependency in getattr(self.callback, "dependencies", []):
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
        """
        Override for augmentations.
        """
        rv = super().get_params(ctx)
        rv = self.augment_help_text(ctx, seen_params=rv)
        return rv


class CSToolsApp(typer.Typer):
    def __init__(self, **passthru):
        passthru["cls"] = CSToolsGroup
        passthru["rich_markup_mode"] = "rich"
        passthru["no_args_is_help"] = True
        super().__init__(**passthru)

    def command(
        self,
        name: Optional[str] = None,
        *,
        dependencies: Optional[List[Callable]] = None,
        # typer kwargs
        cls: Optional[CSToolsCommand] = CSToolsCommand,
        no_args_is_help: bool = True,
        **passthru,
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
            info = typer.models.CommandInfo(name=name, cls=cls, callback=f, no_args_is_help=no_args_is_help, **passthru)
            self.registered_commands.append(info)
            return f

        return decorator


class CSToolsGroup(typer.core.TyperGroup):
    command_class = CSToolsCommand
    group_class = type

    def list_commands(self, ctx: typer.Context) -> List[str]:
        """
        Override so we don't sort alphabetically
        """
        return list(self.commands)
