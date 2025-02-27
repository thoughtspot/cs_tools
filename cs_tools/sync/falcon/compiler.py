from __future__ import annotations

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateColumn
from sqlalchemy.types import TIMESTAMP, Boolean, DateTime, Float, Integer, String, Text

_RESERVED_WORDS = [
    "bool",
    "double",
    "int64",
    "varchar",
    "timestamp",
]


@compiles(Boolean, "sqlite")
def compile_bool(element, compiler, **kw):  # noqa: ARG001
    return "BOOL"


@compiles(Float, "sqlite")
def compile_double(element, compiler, **kw):  # noqa: ARG001
    return "DOUBLE"


@compiles(Integer, "sqlite")
def compile_int(element, compiler, **kw):  # noqa: ARG001
    # DEV NOTE: @boonhapus, 2024/07/07
    # We're going to be really lazy here.
    #
    # Could we dynamically route INT64 and INT32? Sure.
    # Does it matter in practice for our data? No.
    return "INT64"


@compiles(String, "sqlite")
@compiles(Text, "sqlite")
def compile_varchar(element, compiler, **kw):  # noqa: ARG001
    if element.length is None:
        element.length = 0

    return f"VARCHAR({element.length})"


@compiles(TIMESTAMP, "sqlite")
@compiles(DateTime, "sqlite")
def compile_datetime(element, compiler, **kw):  # noqa: ARG001
    return "DATETIME"


@compiles(CreateColumn, "sqlite")
def forget_nullability(element, compiler, **kw):  # noqa: ARG001
    column = element.element

    # Falcon data type don't declare nullability
    column.nullable = True

    # A check hack to avoid unquoted reserved words in SQlite.
    if column.name in _RESERVED_WORDS:
        column.name = f'"{column.name}"'

    return f"{column.name} {compiler.type_compiler.process(column.type)}"
