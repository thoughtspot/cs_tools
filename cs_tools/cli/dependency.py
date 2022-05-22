from typing import Any, Callable, List, Optional

from pydantic.dataclasses import dataclass
from typer.models import ParamMeta
from typer.main import get_click_param
from pydantic import validator
import click
import typer


@dataclass
class Dependency:
    """
    Represents a dependency.

    Attributes
    ----------
    dependency_name: str
      name of the dependent

    dependency: callable
      function to call - the dependency itself

    options: list of typer.Option, default None
      cli options to add to the underlying command

    teardown: callable
      function to call to destruct the dependency itself
    """
    name: str
    dependency: Callable
    options: List[Any] = None
    teardown: Optional[Callable] = None

    @validator('options')
    def _(cls, options, *, values) -> ParamMeta:
        if options is None:
            return None

        params = []

        for option in options:
            if option.param_decls:
                name, *_ = sorted(option.param_decls, key=lambda s: len(s), reverse=True)
            else:
                name = values['name']

            annotation = str if isinstance(option.default, type(...)) else type(option.default)
            param = ParamMeta(name=name.strip('-'), default=option, annotation=annotation)
            click_param, _ = get_click_param(param)
            params.append(click_param)

        return params

    def setup(self, ctx: click.Context, **forwarded) -> Any:
        return self.dependency(ctx, **forwarded)

    def teardown(self, ctx: click.Context) -> Any:
        if self.teardown is None:
            return
        return self.teardown(ctx)

    def __repr__(self) -> str:
        n = self.name
        d = getattr(self.dependency, '__name__', type(self.dependency).__name__)
        o = ', '.join(map(str, self.options))
        return f'<Dependency, {n}={d}({o})>'


def depends(
    dependency_name: str,
    dependency: Callable,
    options: List[typer.Option] = None,
    teardown: Callable = None
) -> Callable:
    """
    Inject a dependency into the underlying command.

    Parameters
    ----------
    dependency_name: str
      name of the dependent

    dependency: callable
      function to call to setup the dependency itself

    options: list of typer.Option, default None
      cli options to add to the underlying command

    teardown: callable
      function to call to destruct the dependency itself
    """
    def decorator(func: Callable) -> Callable:

        if not hasattr(func, 'dependencies'):
            func.dependencies = []

        d = Dependency(
            name=dependency_name,
            dependency=dependency,
            options=options,
            teardown=teardown
        )

        func.dependencies.append(d)
        return func

    return decorator
