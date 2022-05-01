from typing import Any, Callable, List, Optional

from pydantic.dataclasses import dataclass
from typer.models import ParamMeta
from typer.main import get_click_param
from pydantic import validator
from typer import Argument as A_, Option as O_
import click


@dataclass
class Dependency:
    """
    """
    name: str
    to_call: Callable
    options: Optional[List[Any]] = None
    enter_exit: bool = False

    @validator('options')
    def _(cls, v, *, values) -> ParamMeta:
        if v is None:
            return None

        params = []

        for option in v:
            if option.param_decls:
                name, *_ = sorted(option.param_decls, key=lambda s: len(s), reverse=True)
            else:
                name = values['name']

            annotation = str if isinstance(option.default, type(...)) else type(option.default)
            param = ParamMeta(name=name.strip('-'), default=option, annotation=annotation)
            click_param, _ = get_click_param(param)
            params.append(click_param)

        return params

    def setup(self, ctx: click.Context, **kw):
        """
        """
        r = self.to_call(ctx, **kw)

        if self.enter_exit:
            r.__enter__()

    def close(self):
        """
        """
        ctx = click.get_current_context()
        r = getattr(ctx.obj, self.name)

        if self.enter_exit:
            r.__exit__(None, None, None)


def depends(options: Optional[O_] = None, enter_exit: bool = False, **kw):
    """
    Inject a dependency into the underlying command.
    """
    def _wrapper(f):
        if not hasattr(f, '_dependencies'):
            f._dependencies = []

        for k, v in kw.items():
            d = Dependency(name=k, to_call=v, options=options, enter_exit=enter_exit)
            f._dependencies.append(d)

        return f

    return _wrapper
