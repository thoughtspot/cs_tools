from __future__ import annotations

from typing import Any, Optional
import datetime as dt
import logging

from sqlmodel import Field
import pydantic

from cs_tools import validators
from cs_tools.datastructures import ValidatedSQLModel

log = logging.getLogger(__name__)


class FalconTableInfo(ValidatedSQLModel, table=True):
    __tablename__ = "ts_falcon_table_info"

    table_guid: str = Field(primary_key=True)
    ip: str = Field(primary_key=True)
    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    table_name: str = None
    state: str
    database_version: int
    serving_version: int
    building_version: int
    build_duration_s: int
    is_known: bool
    database_status: Optional[str]
    last_uploaded_at: dt.datetime
    num_of_rows: int
    approx_bytes_size: int
    uncompressed_bytes_size: int
    row_skew: int
    num_shards: int
    csv_size_with_replication_mb: float
    replicated: bool

    @pydantic.field_validator("last_uploaded_at", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)
