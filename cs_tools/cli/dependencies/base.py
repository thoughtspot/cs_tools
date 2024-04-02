from __future__ import annotations

from types import TracebackType
from typing import Any, Callable, Optional
import logging

import click
import pydantic
import typer

from cs_tools.datastructures import _GlobalModel

log = logging.getLogger(__name__)


class Dependency(_GlobalModel):
    """
    Functionality to inject before/after invoking commands.

    How does this work?

    Dependencies are attached to commands through the use of the @app.command
    decorator. A dependency can take two forms:

      1. Attaching a callback to call prior to invoking the command.
      2. As an object managing its own context with __enter__ and __exit__.

    CSToolsCommand.invoke will attempt to enter the context for every dependency
    (regardless of form) prior to invoking.

    For an example, see `cs_tools.cli.dependencies.thoughtspot`
    """

    parameters: list[click.Parameter]
    callback: Optional[Callable] = pydantic.Field(default=None)

    def __call__(self, ctx: typer.Context) -> Any:
        return self if self.callback is None else self.callback(ctx)

    def __enter__(self) -> Dependency:
        # if you need access to the context, you can call for it with click.
        #
        # ctx = click.get_current_context()
        raise NotImplementedError

    def __exit__(self, exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType) -> None:
        # if you need access to the context, you can call for it with click.
        #
        # ctx = click.get_current_context()
        raise NotImplementedError
