from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable
import functools as ft
import inspect

if TYPE_CHECKING:
    from collections.abc import Iterable


def count_parameters(func: Callable) -> int:
    """Count the number of parameters in a callable."""
    if isinstance(func, ft.partial):
        return _count_parameters(func.func) + len(func.args)

    if hasattr(func, "__self__"):
        # Bound method
        func = func.__func__  # type: ignore
        return _count_parameters(func) - 1

    return _count_parameters(func)


@ft.lru_cache(maxsize=2048)
def _count_parameters(func: Callable) -> int:
    """Count the number of positional parameters in a callable."""
    parameters: Iterable[inspect.Parameter] = inspect.signature(func).parameters.values()
    return sum(p.kind != inspect.Parameter.KEYWORD_ONLY for p in parameters)


async def invoke(function: Callable[[Any], Any], *params) -> Any:
    """Invoke a function on the event loop."""
    parameter_count = count_parameters(function)
    result = function(*params[:parameter_count])

    if inspect.isawaitable(result):
        result = await result

    return result
