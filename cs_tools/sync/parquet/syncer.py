from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Union
import logging
import pathlib

import pyarrow as pa
import pyarrow.parquet as pq
import pydantic

from cs_tools.sync.base import Syncer

from cs_tools import _types

log = logging.getLogger(__name__)


class Parquet(Syncer):
    """Interact with a Parquet file."""

    __manifest_path__ = pathlib.Path(__file__).parent / "MANIFEST.json"
    __syncer_name__ = "parquet"

    directory: Union[pydantic.DirectoryPath, pydantic.NewPath]
    compression: Literal["GZIP", "SNAPPY"] = "GZIP"

    @pydantic.field_validator("directory", mode="after")
    @classmethod
    def _ensure_directory_exists(cls, value: Union[pydantic.DirectoryPath, pydantic.NewPath]) -> pydantic.DirectoryPath:
        if value.is_file():
            raise ValueError(f"{value.resolve().as_posix()} is a file, not a directory.")

        if not value.exists():
            log.warning(f"The directory '{value.resolve().as_posix()}' does not yet exist, creating it..")
            value.mkdir(parents=True, exist_ok=True)

        return value

    def __repr__(self):
        return f"<ParquetSyncer directory='{self.directory}'>"

    # MANDATORY PROTOCOL MEMBERS

    def load(self, filename: str) -> _types.TableRowsFormat:
        """Read rows from a parquet file."""
        fp = self.directory.joinpath(f"{filename}.parquet")
        table = pq.read_table(fp)
        return table.to_pylist()

    def dump(self, filename: str, *, data: _types.TableRowsFormat) -> None:
        """Write rows to a parquet file."""
        if not data:
            log.warning(f"No data to write to syncer {self}")
            return

        data = pa.Table.from_pylist(data)
        fp = self.directory.joinpath(f"{filename}.parquet")
        pq.write_table(data, fp, compression=self.compression.lower())
