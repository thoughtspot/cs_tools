from __future__ import annotations

from typing import Any, Optional
import collections
import contextlib
import csv
import datetime as dt
import logging
import pathlib
import tempfile

import sqlalchemy as sa

from cs_tools import utils
from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)
DATETIME_FORMAT_ISO_8601 = "%Y-%m-%dT%H:%M:%S.%f"
DATETIME_FORMAT_TSLOAD = "%Y-%m-%d %H:%M:%S"


@contextlib.contextmanager
def temp_csv_for_upload(tmp: pathlib.Path, *, filename: str, data: TableRows, include_header: bool = False):
    """Temporarily create a file for HTTP multipart file uploads."""
    file_opts = {"mode": "w+", "newline": "", "encoding": "utf-8"}

    with tempfile.NamedTemporaryFile(**file_opts, dir=tmp, suffix=f"_{filename}.csv", delete=False) as fd:
        writer = csv.DictWriter(fd, fieldnames=data[0].keys(), delimiter="|")

        if include_header:
            writer.writeheader()

        writer.writerows(data)
        fd.seek(0)

        yield fd

    pathlib.Path(fd.name).unlink()


def format_datetime_values(row: dict[str, Any], *, dt_format: str = DATETIME_FORMAT_ISO_8601) -> dict[str, Any]:
    """Enforce a specific format for datetime values."""
    out = {}

    for key, value in row.items():
        if isinstance(value, dt.datetime):
            value = value.strftime(dt_format)

        out[key] = value

    return out


def batched(prepared_statement, *, session: sa.orm.Session, data: TableRows, max_parameters: int = 999) -> None:
    """Split data across multiple transactions."""
    batchsize = min(5000, max_parameters // len(data[0]))
    rows = []

    for row_number, row in enumerate(data, start=1):
        rows.append(row)

        # Commit every so often.
        if row_number % batchsize == 0:
            stmt = prepared_statement(rows)
            session.execute(stmt)
            session.commit()
            rows = []

    # Final commit, grab the rest of the data rows.
    if rows:
        stmt = prepared_statement(rows)
        session.execute(stmt)
        session.commit()


def generic_upsert(
    target: sa.Table,
    *,
    session: sa.orm.Session,
    data: TableRows,
    unique_key: Optional[list[sa.Column]] = None,
    max_params: int = 999,
) -> None:
    """
    Dialect-agnostic way to UPSERT.

    Performs multiple queries to classify and then properly add records.
    """
    if unique_key is None and not target.primary_key:
        raise ValueError(f"No unique key was supplied for {target}")

    log.debug(f"   TABLE: {target}")
    log.debug(f"DATA IN: {len(data): >7,} rows")
    to_insert = []
    to_update = []

    # SELECT * FROM TABLE WHERE ... IN DATA
    for rows in utils.batched(data, n=max_params // len(target.primary_key)):
        to_filter = collections.defaultdict(set)
        seen_data = []

        for row in rows:
            seen_data.append(row)

            for column in target.primary_key:
                to_filter[column.name].add(row[column.name])

        pk_exp = [column.in_(to_filter[column.name]) for column in target.primary_key]
        select = sa.select(target.primary_key.columns).where(*pk_exp)
        result = session.execute(select)
        batch_row = set(result.all())

        for seen in seen_data:
            pk_hash_value = tuple(v for k, v in seen.items() if k in target.primary_key)

            if pk_hash_value in batch_row:
                to_update.append({(f"alias_{k}" if k in target.primary_key else k): v for k, v in seen.items()})
            else:
                to_insert.append(seen)

    log.debug(f" INSERT: {len(to_insert): >7,} rows")
    log.debug(f" UPDATE: {len(to_update): >7,} rows")

    # INSERT INTO TABLE WHERE NOT EXISTS (SELECT * FROM TABLE) VALUES ( ... )
    for rows in utils.batched(to_insert, n=max_params // len(data[0])):
        session.execute(target.insert().values(rows))
        session.commit()
        rows = []

    # UPDATE      TABLE WHERE     EXISTS (SELECT * FROM TABLE) VALUES ( ... )
    update = target.update().where(*[c.name == sa.bindparam(f"alias_{c.name}") for c in target.primary_key])
    to_update = []

    for rows in utils.batched(to_update, n=max_params // len(data[0])):
        session.execute(update, rows)
        session.commit()
        rows = []
