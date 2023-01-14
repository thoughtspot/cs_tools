from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateColumn
from sqlalchemy.types import Integer, Boolean, String, Float


@compiles(Boolean, "sqlite")
def compile_bool(element, compiler, **kw):
    return "BOOL"


@compiles(Float, "sqlite")
def compile_double(element, compiler, **kw):
    return "DOUBLE"


@compiles(Integer, "sqlite")
def compile_int(element, compiler, **kw):
    return "INT"


@compiles(String, "sqlite")
def compile_varchar(element, compiler, **kw):
    if element.length is None:
        element.length = 0

    return f"VARCHAR({element.length})"


@compiles(CreateColumn, "sqlite")
def forget_nullability(element, compiler, **kw):
    column = element.element

    # Falcon data type don't declare nullability
    column.nullable = True

    return "%s %s" % (column.name, compiler.type_compiler.process(column.type))
