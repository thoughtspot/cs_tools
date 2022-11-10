from typing import Any, Dict
import datetime as dt
import re

import sqlalchemy as sa


RE_LETTERS_ONLY = re.compile(r'[^A-Za-z]')


def infer_schema_from_results(data: Dict[str, Any], tablename: str, metadata: sa.Table) -> sa.Table:
    """
    """
    PY_TO_SQL_MAPPING_TYPES = {
        str: sa.String,
        bool: sa.Boolean,
        float: sa.Float,
        int: sa.Integer,
        dt.date: sa.Date,
        dt.datetime: sa.DateTime,
    }

    columns = []

    for key in data[0].keys():
        max_val = max(row[key] for row in data)
        column_name = RE_LETTERS_ONLY.sub("_", key).lower()
        column_type = PY_TO_SQL_MAPPING_TYPES.get(type(max_val), sa.String)

        if column_type == sa.Float:
            p, _, s = str(max_val).partition(".")
            column_type = column_type(precision=len(p) + len(s))

        if column_type == sa.Integer and max_val > (2 ** 31 - 1):
            column_type = sa.BigInteger

        column = sa.Column(column_name, column_type)
        columns.append(column)

    return sa.Table(tablename, metadata, *columns)
