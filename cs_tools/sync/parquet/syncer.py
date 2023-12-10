from __future__ import annotations

from typing import TYPE_CHECKING, Any
import logging

from pydantic.dataclasses import dataclass
import pyarrow as pa
import pyarrow.parquet as pq

from cs_tools._compat import StrEnum

if TYPE_CHECKING:
    import pathlib

log = logging.getLogger(__name__)


class CompressionTypes(StrEnum):
    gzip = "gzip"
    snappy = "snappy"


@dataclass
class Parquet:
    """
    Interact with Parquet.
    """

    directory: pathlib.Path
    compression: CompressionTypes = CompressionTypes.gzip

    def __post_init_post_parse__(self):
        self.directory = self.directory.resolve()

        if not self.directory.exists():
            log.info(f"{self.directory} does not exist, creating..")

    def resolve_path(self, directive: str) -> pathlib.Path:
        return self.directory.joinpath(f"{directive}.parquet")

    def __repr__(self):
        return f"<Parquet sync: path='{self.directory}'>"

    # MANDATORY PROTOCOL MEMBERS

    @property
    def name(self) -> str:
        return "parquet"

    def load(self, directive: str) -> list[dict[str, Any]]:
        fp = self.resolve_path(directive)
        table = pq.read_table(fp)
        return table.to_pylist()

    def dump(self, directive: str, *, data: list[dict[str, Any]]) -> None:
        if not data:
            log.warning(f"no data to write to syncer {self}")
            return

        data = pa.Table.from_pylist(data)
        fp = self.resolve_path(directive)
        pq.write_table(data, fp, compression=self.compression)
