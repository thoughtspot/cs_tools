from __future__ import annotations

from typing import Any, Literal, get_args, get_origin

import click
import rich
import typer

from cs_tools.cli import custom_types
import cs_tools


def is_literal_type(type_: type[Any]) -> bool:
    """Determine if the type annotation is a Literal."""
    return Literal is not None and get_origin(type_) is Literal


def literal_values(type_: type[Any]) -> tuple[Any, ...]:
    """Fetch the values within the Literal type annotation."""
    return get_args(type_)


class _MonkeyPatchedTyper:
    """Add support for useful and interesting things."""
    og_get_click_type = typer.main.get_click_type

    def __init__(self):
        """Handle patching."""
        typer.rich_utils._get_rich_console = self.override_console_with_ours
        typer.Argument = self.argument_with_better_default
        typer.Option = self.option_with_better_default
        typer.main.get_click_type = self.get_click_type

    def get_click_type(self, *, annotation: Any, parameter_info: typer.models.ParameterInfo) -> click.ParamType:
        # Let Typer handle the basics
        try:
            return _MonkeyPatchedTyper.og_get_click_type(annotation=annotation, parameter_info=parameter_info)        

        # Additional support added by us.
        except RuntimeError:

            # Literal
            if is_literal_type(annotation):
                return custom_types.Literal(choices=literal_values(annotation))

            # CS Tools Custom Types with some pre-requisite configuration
            if isinstance(annotation, custom_types.CustomType):
                return annotation

            # CS Tools Custom Types
            if issubclass(annotation, custom_types.CustomType):
                return annotation()

        # Unreachable, unless neither we nor Typer can handle it.
        raise RuntimeError(f"Type not yet supported: {annotation}")

    def argument_with_better_default(self, default=..., **passthru) -> typer.models.ArgumentInfo:
        """
        Patches:
        - Allow custom type.
        - If required with no default, don't show_default..
        """
        passthru["show_default"] = passthru.get("show_default", default not in (..., None))
        return typer.models.ArgumentInfo(default=default, **passthru)

    def option_with_better_default(self, default=..., *param_decls, **passthru) -> typer.models.OptionInfo:
        """
        Patches:
        - Allow custom type.
        - If required with no default, don't show_default..
        """
        passthru["show_default"] = passthru.get("show_default", default not in (..., None))
        return typer.models.OptionInfo(default=default, param_decls=param_decls, **passthru)

    def override_console_with_ours(self, stderr: bool = False) -> rich.console.Console:
        """
        Patches:
        - There's no formal interface for this, so inject our own console.
        """
        return cs_tools.cli.ux.rich_console


_MonkeyPatchedTyper()
