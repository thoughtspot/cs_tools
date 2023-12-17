from __future__ import annotations

import contextlib
import csv
import pathlib
import tempfile

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
