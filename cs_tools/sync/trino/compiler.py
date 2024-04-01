from __future__ import annotations

import re

from sqlalchemy.ext.compiler import compiles
import sqlalchemy as sa

_REGEX_PRIMARY_KEY_DIRECTIVE = re.compile(r"\W+(PRIMARY KEY.*\))")
# DEV NOTE: @boonhapus, 2024/01/05
# Grab the PRIMARY KEY through the close parenthesis, up through the preceding comma.
#
# CREATE TABLE ts_column_synonym (
#         column_guid VARCHAR NOT NULL,
#         synonym VARCHAR NOT NULL,
#         PRIMARY KEY (column_guid, synonym)
# )
#
#


@compiles(sa.schema.CreateTable, "trino")
def forget_constraints(create_table: sa.schema.CreateTable, compiler: sa.sql.compiler.DDLCompiler, **kw) -> str:
    """Presto/Trino/Starburst don't make use of constraints."""
    # Allow the underlying impementation to craft mostly-appropriate SQL.
    # -> This is a loooot easier than mucking around with the underlying sqlalchemy.Table constraints.
    stmt = compiler.visit_create_table(create_table, **kw)
    # Remove the trailing double newline.
    stmt = stmt.rstrip()
    # Strip off the PRIMARY KEY directive.
    stmt = _REGEX_PRIMARY_KEY_DIRECTIVE.sub("", stmt)
    # Add back in the trailing newline.
    stmt = f"{stmt}\n\n"
    return stmt
