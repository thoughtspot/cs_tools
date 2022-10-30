from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeVar
from typing import Any, Callable, List, Optional
import logging

import click

if TYPE_CHECKING:
    SelfDependency = TypeVar("SelfDependency", bound="Dependency")

log = logging.getLogger(__name__)


@dataclass
class Dependency:
    """
    Functionality to inject prior to invoking commands.

    How does this work?

    Dependencies are attached to commands through the use of the @app.command
    decorator. A dependency can take two forms:

      1. Attaching a callback to call prior to invoking the command.
      2. As an object managing its own context with __enter__ and __exit__.

    CSToolsCommand.invoke will attempt to contextlib.ExitStack.enter_context
    for every dependency (regardless of form) prior to invoking.

    For an example, see `cs_tools.cli.dependencies.thoughtspot`
    """
    parameters: List[click.Parameter]
    callback: Optional[Callable] = field(default=None, init=False)

    def __call__(self, ctx: click.Context) -> Any:
        if self.callback is None:
            return self

        return self.callback(ctx)

    def __enter__(self) -> "SelfDependency":
        # if you need access to the context, either store the current context on the
        # object, or call for it.
        #
        # ctx = click.get_current_context()
        raise NotImplementedError

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        # if you need access to the context, either store the current context on the
        # object, or call for it.
        #
        # ctx = click.get_current_context()
        raise NotImplementedError
