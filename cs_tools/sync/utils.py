from __future__ import annotations

import contextlib
import csv
import pathlib
import tempfile

import sqlalchemy as sa

from cs_tools.sync.types import TableRows


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
    MERG_INTO_TEMPLATE = (
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

    stmt = MERG_INTO_TEMPLATE.format(
        target=target.name,
        values=select_from_values.compile(),
        column_names=", ".join(column.name for column in target.columns),
        search_expression=" AND ".join(f"source.{column.name} = target.{column.name}" for column in primary),
        insert_column_list=", ".join(column.name for column in target.columns),
        insert_column_data=", ".join(f"source.{column.name}" for column in target.columns),
        update_mapped_data=", ".join(f"{column.name} = source.{column.name}" for column in secondary),
    )

    return sa.text(stmt)
