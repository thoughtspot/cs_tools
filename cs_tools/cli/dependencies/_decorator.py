from __future__ import annotations

from typing import Any, Callable
import functools as ft
import inspect

import click
import typer

from cs_tools import utils


def _inject_signature_with_dependencies(original_signature: inspect.Signature, dependencies: Any) -> inspect.Signature:
    """Inject the original signature with dependencies' parameters."""
    IS_TYPER_OPTION = ft.partial(lambda _: isinstance(_, typer.models.OptionInfo))

    injected_parameters = list(original_signature.parameters.values())

    # ENSURE DEPENDENCIES HAVE THEIR OPTIONS REGISTERED.
    for resource in dependencies.values():
        annotations = inspect.get_annotations(type(resource), eval_str=True)

        for option_name, option_info in inspect.getmembers(resource, predicate=IS_TYPER_OPTION):
            injected_parameters.append(
                inspect.Parameter(
                    name=option_name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=option_info,
                    annotation=annotations[option_name],
                )
            )

    return original_signature.replace(parameters=injected_parameters)


def depends_on(**resources: Any) -> Callable:
    """
    Decorator factory that injects dependencies into the context.

    Usage:
        @app.command()
        @depends_on(db=Database())
        def my_command(ctx: Context): ...
    """

    def decorator(fn: Callable) -> Callable:
        original_signature = inspect.signature(fn)
        injected_signature = _inject_signature_with_dependencies(original_signature, resources)

        @ft.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = click.get_current_context()

            if not isinstance(ctx.obj, utils.State):
                ctx.obj = utils.State()

            # ENSURE DEPENDENCIES ARE SET UP ON THE FIRST COMMAND INVOCATION.
            for dependency_name, resource in resources.items():
                if getattr(ctx.obj, dependency_name, None) is None:
                    resource.__with_user_setup__(ctx, name=dependency_name)
                    ctx.with_resource(resource)

            # DON'T PASS THE DEPENDECIES' PARAMETERS TO THE UNDERLYING FUNCTION.
            kwargs = {k: v for k, v in kwargs.items() if k in original_signature.parameters}

            return fn(*args, **kwargs)

        # ENSURE THE CLI CODE CAN SEE THE INJECTED PARAMETERS
        wrapper.__signature__ = injected_signature  # type: ignore[attr-defined]

        return wrapper

    return decorator
