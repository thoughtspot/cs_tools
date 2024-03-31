from __future__ import annotations

import rich
import typer

import cs_tools


class _MonkeyPatchedTyper:
    """
    Add support for useful and interesting things.
    """

    def __init__(self):
        self._original_get_rich_console = typer.rich_utils._get_rich_console
        self._original_get_click_type = typer.main.get_click_type
        self._patch()

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

    def override_console_with_ours(self, stderr: bool = False) -> rich.console.Console:  # noqa: ARG002
        """
        Patches:
        - There's no formal interface for this, so inject our own console.
        """
        return cs_tools.cli.ux.rich_console

    def _patch(self) -> None:
        """Handle patching."""
        typer.rich_utils._get_rich_console = self.override_console_with_ours
        typer.Argument = self.argument_with_better_default
        typer.Option = self.option_with_better_default


_MonkeyPatchedTyper()
