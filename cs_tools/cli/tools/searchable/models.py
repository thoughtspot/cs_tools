from __future__ import annotations

from typing import Any, Optional, Union
import datetime as dt
import logging
import zoneinfo

from sqlalchemy.schema import Column
from sqlalchemy.types import TIMESTAMP, BigInteger, Text
from sqlmodel import Field
import pydantic

from cs_tools import validators
from cs_tools.datastructures import ValidatedSQLModel

log = logging.getLogger(__name__)


class Cluster(ValidatedSQLModel, table=True):
    __tablename__ = "ts_cluster"
    cluster_guid: str = Field(primary_key=True)
    url: validators.AnyHttpURLStr
    timezone: str

    @pydantic.field_validator("timezone", mode="before")
    @classmethod
    def tzname_only(cls, value: Union[str, zoneinfo.ZoneInfo]) -> str:
        if isinstance(value, zoneinfo.ZoneInfo):
            return value.key
        return value


class Org(ValidatedSQLModel, table=True):
    __tablename__ = "ts_org"
    cluster_guid: str = Field(primary_key=True)
    org_id: int = Field(sa_column=Column(BigInteger, autoincrement=False, primary_key=True))
    name: str
    description: Optional[str]

    @pydantic.field_validator("description", mode="before")
    @classmethod
    def remove_leading_trailing_spaces(cls, value: Any) -> Optional[str]:
        if not value:
            return None
        return value.strip()


class User(ValidatedSQLModel, table=True):
    __tablename__ = "ts_user"
    cluster_guid: str = Field(primary_key=True)
    user_guid: str = Field(primary_key=True)
    username: str
    email: Optional[str]
    display_name: str
    sharing_visibility: str
    created: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    modified: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    user_type: str

    @pydantic.field_validator("created", "modified", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)


class Group(ValidatedSQLModel, table=True):
    __tablename__ = "ts_group"
    cluster_guid: str = Field(primary_key=True)
    org_id: int = Field(primary_key=True)
    group_guid: str = Field(primary_key=True)
    group_name: str
    description: Optional[str] = Field(sa_column=Column(Text, info={"length_override": "MAX"}))
    display_name: str
    sharing_visibility: str
    created: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    modified: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    group_type: str

    @pydantic.field_validator("description", mode="before")
    @classmethod
    def remove_leading_trailing_spaces(cls, value: Any) -> Optional[str]:
        if not value:
            return None
        return value.strip()

    @pydantic.field_validator("created", "modified", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)


class GroupPrivilege(ValidatedSQLModel, table=True):
    __tablename__ = "ts_group_privilege"
    cluster_guid: str = Field(primary_key=True)
    group_guid: str = Field(primary_key=True)
    privilege: str = Field(primary_key=True)


class OrgMembership(ValidatedSQLModel, table=True):
    __tablename__ = "ts_xref_org"
    cluster_guid: str = Field(primary_key=True)
    user_guid: str = Field(primary_key=True)
    org_id: int = Field(primary_key=True)


class GroupMembership(ValidatedSQLModel, table=True):
    __tablename__ = "ts_xref_principal"
    cluster_guid: str = Field(primary_key=True)
    principal_guid: str = Field(primary_key=True)
    group_guid: str = Field(primary_key=True)


class Tag(ValidatedSQLModel, table=True):
    __tablename__ = "ts_tag"
    cluster_guid: str = Field(primary_key=True)
    org_id: int = Field(primary_key=True)
    tag_guid: str = Field(primary_key=True)
    tag_name: str
    author_guid: str
    created: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    modified: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    color: Optional[str]

    @pydantic.field_validator("created", "modified", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)


class DataSource(ValidatedSQLModel, table=True):
    __tablename__ = "ts_data_source"
    cluster_guid: str = Field(primary_key=True)
    org_id: int = Field(primary_key=True)
    data_source_guid: str = Field(primary_key=True)
    dbms_type: str
    name: str
    description: Optional[str]

    @pydantic.field_validator("description", mode="before")
    @classmethod
    def remove_leading_trailing_spaces(cls, value: Any) -> Optional[str]:
        if not value:
            return None
        return value.strip()

    @pydantic.field_validator("dbms_type", mode="before")
    @classmethod
    def clean_dbms_type(cls, value: Any) -> str:
        return "FALCON" if value == "DEFAULT" else value.removeprefix("RDBMS_")


class MetadataObject(ValidatedSQLModel, table=True):
    __tablename__ = "ts_metadata_object"
    cluster_guid: str = Field(primary_key=True)
    org_id: int = Field(primary_key=True)
    object_guid: str = Field(primary_key=True)
    name: str = Field(sa_column=Column(Text, info={"length_override": "MAX"}))
    description: Optional[str] = Field(sa_column=Column(Text, info={"length_override": "MAX"}))
    author_guid: str
    created: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    modified: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    object_type: str
    object_subtype: Optional[str]
    data_source_guid: Optional[str]
    is_sage_enabled: Optional[bool]
    is_verified: Optional[bool]
    is_version_controlled: Optional[bool]

    @pydantic.field_validator("description", mode="before")
    @classmethod
    def clean_empty_or_whitespace_description(cls, value: Any) -> Optional[str]:
        if not value:
            return None
        return value.strip()

    @pydantic.field_validator("created", "modified", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)


class MetadataColumn(ValidatedSQLModel, table=True):
    __tablename__ = "ts_metadata_column"
    cluster_guid: str = Field(primary_key=True)
    column_guid: str = Field(primary_key=True)
    object_guid: str
    column_name: str
    description: Optional[str] = Field(sa_column=Column(Text, info={"length_override": "MAX"}))
    data_type: str
    column_type: str
    additive: bool
    aggregation: str
    hidden: bool
    # synonyms
    index_type: str
    geo_config: Optional[str]
    index_priority: int
    format_pattern: Optional[str]
    currency_type: Optional[str]
    attribution_dimension: bool
    spotiq_preference: bool
    calendar_type: Optional[str]
    # custom_sort: ... ???
    # value_casing: ... ???
    is_formula: bool

    @pydantic.field_validator("description", mode="before")
    @classmethod
    def remove_leading_trailing_spaces(cls, value: Any) -> Optional[str]:
        if not value:
            return None
        return value.strip()

    @pydantic.field_validator("index_priority")
    @classmethod
    def clamp_1_to_10(cls, value: int, info: pydantic.ValidationInfo) -> int:
        if 1 <= value <= 10:
            return value

        log.warning(
            f"INDEX_PRIORITY is clamped between 1 and 10 in ThoughtSpot, though no validation occurs in the UI. The "
            f"column '{info.data['column_name']}' has the value of {int(value):,}. "
            f"[COLUMN {info.data['column_guid']} IN TABLE {info.data['object_guid']}]"
        )

        return max(1, min(10, value))


class ColumnSynonym(ValidatedSQLModel, table=True, frozen=True):
    """Representation of a Table's column's synonym."""

    __tablename__ = "ts_column_synonym"
    cluster_guid: str = Field(primary_key=True)
    column_guid: str = Field(primary_key=True)
    synonym: str = Field(primary_key=True)


class MetadataTML(ValidatedSQLModel, table=True):
    __tablename__ = "ts_metadata_tml"
    cluster_guid: str = Field(primary_key=True)
    org_id: int = Field(0, primary_key=True)
    snapshot_date: dt.date = Field(primary_key=True)
    object_guid: str = Field(primary_key=True)
    name: str
    object_type: Optional[str] = None
    object_subtype: Optional[str] = None
    author_guid: Optional[str] = None
    created: Optional[dt.datetime] = Field(None, sa_column=Column(TIMESTAMP))
    modified: Optional[dt.datetime] = Field(None, sa_column=Column(TIMESTAMP))
    tml_blob: str
    tml_format: str  # JSON, YAML


class TaggedObject(ValidatedSQLModel, table=True):
    __tablename__ = "ts_tagged_object"
    cluster_guid: str = Field(primary_key=True)
    object_guid: str = Field(primary_key=True)
    tag_guid: str = Field(primary_key=True)


class DependentObject(ValidatedSQLModel, table=True):
    __tablename__ = "ts_dependent_object"
    cluster_guid: str = Field(primary_key=True)
    dependent_guid: str = Field(primary_key=True)
    column_guid: str = Field(primary_key=True)
    name: str = Field(sa_column=Column(Text, info={"length_override": "MAX"}))
    description: Optional[str] = Field(sa_column=Column(Text, info={"length_override": "MAX"}))
    author_guid: str
    created: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    modified: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    object_type: str
    object_subtype: Optional[str]
    is_verified: Optional[bool]
    is_version_controlled: Optional[bool]

    @pydantic.field_validator("description", mode="before")
    @classmethod
    def remove_leading_trailing_spaces(cls, value: Any) -> Optional[str]:
        if not value:
            return None
        return value.strip()

    @pydantic.field_validator("created", "modified", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)


class SharingAccess(ValidatedSQLModel, table=True):
    __tablename__ = "ts_sharing_access"
    cluster_guid: str = Field(primary_key=True)
    sk_dummy: str = Field(
        primary_key=True,
        sa_column_kwargs={"comment": "shared_to_* is a composite PK, but can be nullable, so we need a dummy"},
    )
    object_guid: str
    shared_to_user_guid: Optional[str]
    shared_to_group_guid: Optional[str]
    permission_type: str
    share_mode: str  # READ_ONLY, MODIFY
    share_type: Optional[str]  # OBJECT_LEVEL_SECURITY, COLUMN_LEVEL_SECURITY


class AuditLogs(ValidatedSQLModel, table=True):
    __tablename__ = "ts_audit_logs"
    cluster_guid: str = Field(primary_key=True)
    org_id: int = Field(0, primary_key=True)
    sk_dummy: str = Field(primary_key=True)
    timestamp: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    log_type: str
    user_guid: Optional[str]
    description: str
    details: str = Field(sa_column_kwargs={"comment": "JSON body of the Log Event"})


class BIServer(ValidatedSQLModel, table=True):
    __tablename__ = "ts_bi_server"
    cluster_guid: str = Field(primary_key=True)
    sk_dummy: str = Field(primary_key=True)
    org_id: int = 0
    incident_id: str
    timestamp: dt.datetime = Field(sa_column=Column(TIMESTAMP))
    url: Optional[str]
    http_response_code: Optional[int]
    browser_type: Optional[str]
    browser_version: Optional[str]
    client_type: Optional[str]
    client_id: Optional[str]
    answer_book_guid: Optional[str]
    viz_id: Optional[str] = Field(sa_column=Column(Text, info={"length_override": "MAX"}))
    user_id: Optional[str]
    user_action: Optional[str]
    query_text: Optional[str] = Field(sa_column=Column(Text, info={"length_override": "MAX"}))
    response_size: Optional[int] = Field(sa_column=Column(BigInteger))
    latency_us: Optional[int] = Field(sa_column=Column(BigInteger))
    impressions: Optional[float]

    @pydantic.field_validator("timestamp", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)

    @pydantic.field_validator("client_type", "user_action", mode="after")
    @classmethod
    def ensure_is_case_sensitive_thoughtspot_enum_value(cls, value: Optional[str]) -> Optional[str]:
        # Why not Annotated[str, pydantic.StringContraints(to_upper=True)] ?
        # sqlmodel#67: https://github.com/tiangolo/sqlmodel/issues/67
        return None if value is None else value.upper()

    @pydantic.field_validator("url", "browser_type", "browser_version", mode="after")
    @classmethod
    def ensure_is_uniform_lowered_value(cls, value: Optional[str]) -> Optional[str]:
        # Why not Annotated[str, pydantic.StringContraints(to_lower=True)] ?
        # sqlmodel#67: https://github.com/tiangolo/sqlmodel/issues/67
        return None if value is None else value.lower()

    @pydantic.field_serializer("query_text")
    def export_reserved_characters_are_escaped(self, query_text: Optional[str]) -> Optional[str]:
        if query_text is None:
            return query_text
        reserved_characters = ("\\",)

        for character in reserved_characters:
            query_text = query_text.replace(character, f"\\{character}")

        return query_text

class AIStats(ValidatedSQLModel, table=True):
    __tablename__ = "ts_ai_stats"
    cluster_guid: str = Field(primary_key=True)
    sk_dummy: str = Field(primary_key=True)
    answer_session_id : Optional[str]
    query_latency : Optional[int]
    system_latency : Optional[int]
    connection : Optional[str]
    connection_id : Optional[str]
    db_auth_type : Optional[str]
    db_type : Optional[str]
    error_message : Optional[str]
    external_database_query_id : Optional[str]
    impressions : Optional[int]
    is_billable : Optional[bool]
    is_system : Optional[bool]
    model : Optional[str]
    model_id : Optional[str]
    object : Optional[str]
    object_id : Optional[str]
    object_subtype : Optional[str]
    object_type : Optional[str]
    org : Optional[str]
    org_id: int = 0
    query_count : Optional[int]
    query_end_time : dt.datetime = Field(sa_column = Column(TIMESTAMP))
    query_errors : Optional[int]
    query_start_time : dt.datetime = Field(sa_column =Column(TIMESTAMP))
    query_status : Optional[str]
    sql_query : Optional[str] = Field(sa_column = Column(Text, info = {"length_override": "MAX"}))
    thoughtspot_query_id :Optional[str]
    thoughtspot_start_time : dt.datetime = Field(sa_column =Column(TIMESTAMP))
    credits : Optional[int]
    nums_rows_fetched : Optional[int]
    trace_id : Optional[str]
    user : Optional[str]
    user_action : Optional[str]
    user_action_count : Optional[int]
    user_count : Optional[int]
    user_display_name : Optional[str]
    user_id : Optional[str]
    visualization_id : Optional[str] 


    @pydantic.field_validator("thoughtspot_start_time", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)

    @pydantic.field_validator("user_action", mode="after")
    @classmethod
    def ensure_is_case_sensitive_thoughtspot_enum_value(cls, value: Optional[str]) -> Optional[str]:
        # Why not Annotated[str, pydantic.StringContraints(to_upper=True)] ?
        # sqlmodel#67: https://github.com/tiangolo/sqlmodel/issues/67
        return None if value is None else value.upper()
    
    @pydantic.field_serializer("sql_query")
    def export_reserved_characters_are_escaped(self, sql_query: Optional[str]) -> Optional[str]:
        if sql_query is None:
            return sql_query
        reserved_characters = ("\\",)

        for character in reserved_characters:
            sql_query = sql_query.replace(character, f"\\{character}")
        
        return sql_query

METADATA_MODELS = [
    Cluster,
    Org,
    User,
    OrgMembership,
    Group,
    GroupPrivilege,
    GroupMembership,
    Tag,
    DataSource,
    MetadataObject,
    MetadataColumn,
    ColumnSynonym,
    TaggedObject,
    DependentObject,
    SharingAccess,
]

PRINCIPAL_MODELS = [
    Org,
    User,
    OrgMembership,
    Group,
    GroupPrivilege,
    GroupMembership,
]
