from __future__ import annotations

from typing import TYPE_CHECKING, Any

import typer

import cs_tools
import cs_tools.cli.ux

if TYPE_CHECKING:
    import click
    import rich


class _ArgumentInfo(typer.models.ArgumentInfo):
    """Allow custom type."""

    def __init__(self, *a, custom_type: Any = None, **kw):
        self.custom_type = custom_type
        super().__init__(*a, **kw)


class _OptionInfo(typer.models.OptionInfo):
    """Allow custom type."""

    def __init__(self, *a, custom_type: Any = None, **kw):
        self.custom_type = custom_type
        super().__init__(*a, **kw)


class _MonkeyPatchedTyper:
    """
    Add support for useful and interesting things.

    We're monkeypatching Typer because @tiangolo is AFK Maintainer and won't assign co-maintainers.

    We are allowing typer.Argument and typer.Option to implement the custom_type keyword
    here. This means we can inherit from click.ParamType and implement custom argument
    conversion functionality.

    This is addressed in #77 - https://github.com/tiangolo/typer/issues/77
    """

    def __init__(self):
        self._original_get_rich_console = typer.rich_utils._get_rich_console
        self._original_get_click_type = typer.main.get_click_type
        self._patch()

    def supersede_get_click_type(self, *, annotation: Any, parameter_info: typer.main.ParameterInfo) -> click.ParamType:
        """ """
        if hasattr(parameter_info, "custom_type") and parameter_info.custom_type is not None:
            return parameter_info.custom_type
        else:
            return self._original_get_click_type(annotation=annotation, parameter_info=parameter_info)

    def argument_with_custom_type(self, default, **passthru) -> _ArgumentInfo:
        """
        Patches:
        - Allow custom type.
        - If required with no default, don't show_default..
        """
        passthru["show_default"] = passthru.get("show_default", default not in (..., None))
        return _ArgumentInfo(default=default, **passthru)

    def option_with_custom_type(self, default, *param_decls, **passthru) -> _OptionInfo:
        """
        Patches:
        - Allow custom type.
        - If required with no default, don't show_default..
        """
        passthru["show_default"] = passthru.get("show_default", default not in (..., None))
        return _OptionInfo(default=default, param_decls=param_decls, **passthru)

    def override_console_with_ours(self, stderr: bool = False) -> rich.console.Console:  # noqa: ARG002
        """
        Patches:
        - There's no formal interface for this, so inject our own console.
        """
        return cs_tools.cli.ux.rich_console

    def _patch(self) -> None:
        """Handle patching."""
        typer.rich_utils._get_rich_console = self.override_console_with_ours
        typer.main.get_click_type = self.supersede_get_click_type
        typer.Argument = self.argument_with_custom_type
        typer.Option = self.option_with_custom_type


_MonkeyPatchedTyper()
