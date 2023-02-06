from typing import Any

import typer
import click

_get_click_type = typer.main.get_click_type


def supersede_get_click_type(*, annotation: Any, parameter_info: typer.main.ParameterInfo) -> click.ParamType:
    """
    Monkeypatch Typer because @tiangolo is AFK Maintainer and won't assign co-maintainers.

    We are allowing typer.Argument and typer.Option to implement the custom_type keyword
    here. This means we can inherit from click.ParamType and implement custom argument
    conversion functionality.

    This is addressed in #77 - https://github.com/tiangolo/typer/issues/77
    """
    if hasattr(parameter_info, "custom_type") and parameter_info.custom_type is not None:
        return parameter_info.custom_type
    else:
        return _get_click_type(annotation=annotation, parameter_info=parameter_info)


typer.main.get_click_type = supersede_get_click_type
