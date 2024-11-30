from __future__ import annotations

from typing import Any
import datetime as dt
import logging

from sqlmodel import Field
import pydantic

from cs_tools import validators
from cs_tools._compat import StrEnum
from cs_tools.datastructures import ValidatedSQLModel

log = logging.getLogger(__name__)


class LiteralOperation(StrEnum):
    IDENTIFY = "IDENTIFY"
    REVERT = "REVERT"
    REMOVE = "REMOVE"


class ArchiverReport(ValidatedSQLModel, table=True):
    __tablename__ = "archiver_report"

    type: str = Field(primary_key=True)
    guid: str = Field(primary_key=True)
    modified: dt.datetime = Field(primary_key=True)
    author_guid: str
    author: str
    name: str
    operation: LiteralOperation

    @pydantic.field_validator("modified", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)
