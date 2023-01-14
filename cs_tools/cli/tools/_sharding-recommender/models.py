import datetime as dt
import logging

from sqlmodel import SQLModel, Field

from cs_tools.util import to_datetime

log = logging.getLogger(__name__)


class FalconTableInfo(SQLModel, table=True):
    __tablename__ = "ts_falcon_table_info"
    table_guid: str = Field(primary_key=True)
    ip: str = Field(primary_key=True)
    database_name: str
    schema_name: str
    table_name: str
    state: str
    database_version: int
    serving_version: int
    building_version: int
    build_duration_s: int
    is_known: bool
    database_status: str
    last_uploaded_at: dt.datetime
    num_of_rows: int
    approx_bytes_size: int
    uncompressed_bytes_size: int
    row_skew: int
    num_shards: int
    csv_size_with_replication_mb: float
    replicated: bool

    @classmethod
    def from_api_v1(cls, data) -> "FalconTableInfo":
        data = {
            "table_guid": data["guid"],
            "ip": "all" if data.get("ip") == -1 else data.get("ip", None),
            "database_name": data.get("database"),
            "schema_name": data.get("schema"),
            "table_name": data.get("name"),
            "state": data.get("state"),
            "database_version": data.get("databaseVersion"),
            "serving_version": data.get("servingVersion"),
            "building_version": data.get("buildingVersion"),
            "build_duration_s": data.get("buildDuration"),
            "is_known": data.get("isKnown"),
            "database_status": data.get("databaseStatus"),
            "last_uploaded_at": to_datetime(data.get("lastUploadedAt", 0), unit="us"),
            "num_of_rows": data.get("numOfRows"),
            "approx_bytes_size": data.get("approxByteSize"),
            "uncompressed_bytes_size": data.get("uncompressedByteSize"),
            "row_skew": data.get("rowSkew"),
            "num_shards": data.get("numShards"),
            "csv_size_with_replication_mb": data.get("csvSizeWithReplicationMB"),
            "replicated": data.get("replicated"),
        }
        return cls(**data)
