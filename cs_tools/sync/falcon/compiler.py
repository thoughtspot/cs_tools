from __future__ import annotations

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateColumn
from sqlalchemy.types import Boolean, Float, Integer, String, Text


@compiles(Boolean, "sqlite")
def compile_bool(element, compiler, **kw):  # noqa: ARG001
    return "BOOL"


@compiles(Float, "sqlite")
def compile_double(element, compiler, **kw):  # noqa: ARG001
    return "DOUBLE"


@compiles(Integer, "sqlite")
def compile_int(element, compiler, **kw):  # noqa: ARG001
    return "INT"


@compiles(String, "sqlite")
@compiles(Text, "sqlite")
def compile_varchar(element, compiler, **kw):  # noqa: ARG001
    if element.length is None:
        element.length = 0

    return f"VARCHAR({element.length})"


@compiles(CreateColumn, "sqlite")
def forget_nullability(element, compiler, **kw):  # noqa: ARG001
    column = element.element

    # Falcon data type don't declare nullability
    column.nullable = True

    return f"{column.name} {compiler.type_compiler.process(column.type)}"
