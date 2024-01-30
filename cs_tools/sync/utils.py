from __future__ import annotations

from typing import Optional
import collections
import contextlib
import csv
import logging
import pathlib
import tempfile
import textwrap

import sqlalchemy as sa

from cs_tools import utils
from cs_tools.sync.types import TableRows

log = logging.getLogger(__name__)


@contextlib.contextmanager
def make_tempfile_for_upload(directory: pathlib.Path, *, filename: str, data: TableRows, include_header: bool = False):
    """Temporarily create a file for HTTP multipart file uploads."""
    with tempfile.NamedTemporaryFile(mode="w+", dir=directory, suffix=f"_{filename}.csv.gz", delete=False) as fd:
        writer = csv.DictWriter(fd, fieldnames=data[0].keys(), delimiter="|")

        if include_header:
            writer.writeheader()

        writer.writerows(data)
        fd.seek(0)

        yield fd

    pathlib.Path(fd.name).unlink()


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
    stmt = prepared_statement(rows)
    session.execute(stmt)
    session.commit()


def merge_into(target: sa.Table, data: TableRows) -> sa.TextClause:
    """
    Implements the MERGE INTO expression.

    The USING clause is a SELECT FROM VALUEs.

    Further reading:
    https://modern-sql.com/caniuse/merge
    """
    # fmt: off
    MERGE_INTO_TEMPLATE = textwrap.dedent(
        """
        MERGE INTO {target} AS target
        USING ({values})    AS source
           ON {search_expression}
         WHEN NOT MATCHED THEN INSERT ({insert_column_list}) VALUES ({insert_column_data})
         WHEN     MATCHED THEN UPDATE SET {update_mapped_data}
        """
    )
    # fmt: on

    primary = [column for column in target.columns if column.primary_key]
    secondary = [column for column in target.columns if not column.primary_key]

    # All columns are Primary Keys.
    if not secondary:
        secondary = primary

    # Generate the SELECT FROM VALUES clause
    select_from_values = sa.select(
        sa.values(*target.columns, name="t", literal_binds=True).data([tuple(row.values()) for row in data])
    )

    stmt = MERGE_INTO_TEMPLATE.format(
        target=target.name,
        values=select_from_values.compile(),
        column_names=", ".join(column.name for column in target.columns),
        search_expression=" AND ".join(f"source.{column.name} = target.{column.name}" for column in primary),
        insert_column_list=", ".join(column.name for column in target.columns),
        insert_column_data=", ".join(f"source.{column.name}" for column in target.columns),
        update_mapped_data=", ".join(f"{column.name} = source.{column.name}" for column in secondary),
    )

    return sa.text(stmt)


def generic_upsert(
    target: sa.Table,
    *,
    session: sa.orm.Session,
    data: TableRows,
    unique_key: Optional[list[sa.Column]] = None,
) -> None:
    """
    Dialect-agnostic way to UPSERT.

    Performs multiple queries to classify and then properly add records.
    """
    if unique_key is None and not target.primary_key:
        raise ValueError()

    log.debug(f"DATA IN: {len(data): >7,} rows")
    to_insert = []
    to_update = []

    # SELECT * FROM TABLE WHERE ... IN DATA
    for rows in utils.batched(data, n=999 // len(target.primary_key)):
        to_filter = collections.defaultdict(set)
        seen_data = []

        for column in target.primary_key:
            for row in rows:
                to_filter[column.name].add(row[column.name])
                seen_data.append(row)

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
    for rows in utils.batched(to_insert, n=999 // len(data[0])):
        session.execute(target.insert().values(rows))
        session.commit()
        rows = []

    # UPDATE      TABLE WHERE     EXISTS (SELECT * FROM TABLE) VALUES ( ... )
    update = target.update().where(*[c.name == sa.bindparam(f"alias_{c.name}") for c in target.primary_key])
    to_update = []

    for rows in utils.batched(to_update, n=999 // len(data[0])):
        session.execute(update, rows)
        session.commit()
        rows = []
