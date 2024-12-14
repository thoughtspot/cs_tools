from __future__ import annotations

from collections.abc import Sequence
from typing import Any
import datetime as dt
import logging

import click

log = logging.getLogger(__name__)


class CustomType(click.ParamType):
    """
    A distinct type for use on the CLI.

    Is used as a click_type, but without the explicit instance creation.
    """

    name = "CustomType"

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> Any:
        """Take raw input string and converts it to the desired type."""
        raise NotImplementedError


class Literal(CustomType):
    """Only accept one of a few choices."""

    def __init__(self, choices: Sequence[str]) -> None:
        self.choices = choices

    def get_metavar(self, param: click.Parameter) -> str:  # noqa: ARG002
        """Example usage of the parameter to display on the CLI."""
        return "|".join(self.choices)

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> str:
        """Validate that the CLI input is one of the accepted values."""
        original_value = value
        choices = self.choices

        if ctx is not None and ctx.token_normalize_func is not None:
            value = ctx.token_normalize_func(value)
            choices = [ctx.token_normalize_func(choice) for choice in self.choices]

        if value not in choices:
            self.fail(
                message=f"Invalid value, should be one of {self.choices}, got '{original_value}'",
                param=param,
                ctx=ctx,
            )

        return original_value


class Date(CustomType):
    """Convert STR to DATE."""

    name = "DATE"

    def get_metavar(self, param: click.Parameter) -> str:  # noqa: ARG002
        """Example usage of the parameter to display on the CLI."""
        return "YYYY-MM-DD"

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> dt.date:
        """Coerce ISO-8601 date strings into a datetime.datetime.date."""
        try:
            date = dt.date.fromisoformat(value)
        except ValueError:
            self.fail(message="Invalid format, please use YYYY-MM-DD", param=param, ctx=ctx)

        return date
