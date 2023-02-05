import datetime as dt
import logging

from sqlmodel import SQLModel, Field

log = logging.getLogger(__name__)


class PerformanceEvent(SQLModel, table=True):
    __tablename__ = "ts_performance_event"
    request_start_time: dt.datetime = Field(primary_key=True)
    metadata_guid: str = Field(primary_key=True)
    user_guid: str = Field(primary_key=True)
    performance_run_id: int
    metadata_type: str
    is_success: bool
    response_received_time: dt.datetime
    latency: float
