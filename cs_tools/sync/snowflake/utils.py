from __future__ import annotations

import sqlalchemy as sa


def parse_field(column: sa.Column) -> str:
    """Return the Snowflake expression to select the given column from a staged Parquet document."""
    field = f"$1:{column.key}"

    if isinstance(column.type, sa.DateTime):
        # Parquet stores datetime64-ntz as a millisecond timestamp
        field = f"TO_TIMESTAMP({field}::INTEGER, 6)"

    return field
