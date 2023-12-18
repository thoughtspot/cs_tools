from typing import Optional, List
import datetime as dt
import logging

from pydantic.datetime_parse import parse_datetime
from pydantic import validator
from sqlmodel import SQLModel, Field

log = logging.getLogger(__name__)


class ArchiverReport(SQLModel, table=True):
    __tablename__ = "archiver_report"
    type: str = Field(primary_key=True)
    guid: str = Field(primary_key=True)
    modified: dt.datetime = Field(primary_key=True)
    author_guid = str
    author = str
    name = str

    @validator("modified", pre=True)
    def _naive_timestamp(cls, timestamp: int) -> dt.datetime:
        return parse_datetime(timestamp).replace(microsecond=0)
