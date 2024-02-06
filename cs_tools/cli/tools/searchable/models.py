from __future__ import annotations

from typing import Any, Optional
import datetime as dt
import logging

from sqlalchemy.schema import Column
from sqlalchemy.types import BigInteger
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


class Org(ValidatedSQLModel, table=True):
    __tablename__ = "ts_org"
    cluster_guid: str = Field(primary_key=True)
    org_id: int = Field(sa_column=Column(BigInteger, autoincrement=False, primary_key=True))
    name: str
    description: Optional[str]


class User(ValidatedSQLModel, table=True):
    __tablename__ = "ts_user"
    cluster_guid: str = Field(primary_key=True)
    user_guid: str = Field(primary_key=True)
    username: str
    email: Optional[str]
    display_name: str
    sharing_visibility: str
    created: dt.datetime
    modified: dt.datetime
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
    description: Optional[str]
    display_name: str
    sharing_visibility: str
    created: dt.datetime
    modified: dt.datetime
    group_type: str

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
    created: dt.datetime
    modified: dt.datetime
    color: Optional[str]

    @pydantic.field_validator("created", "modified", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)


class MetadataObject(ValidatedSQLModel, table=True):
    __tablename__ = "ts_metadata_object"
    cluster_guid: str = Field(primary_key=True)
    org_id: int = Field(primary_key=True)
    object_guid: str = Field(primary_key=True)
    name: str
    description: Optional[str]
    author_guid: str
    created: dt.datetime
    modified: dt.datetime
    object_type: str
    object_subtype: Optional[str]

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
    description: Optional[str]
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
    spotiq_preference: str
    calendar_type: Optional[str]
    is_formula: bool


class ColumnSynonym(ValidatedSQLModel, table=True, frozen=True):
    """Representation of a Table's column's synonym."""

    __tablename__ = "ts_column_synonym"
    cluster_guid: str = Field(primary_key=True)
    column_guid: str = Field(primary_key=True)
    synonym: str = Field(primary_key=True)
    # is_sage_generated: bool


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
    name: str
    description: Optional[str]
    author_guid: str
    created: dt.datetime
    modified: dt.datetime
    object_type: str

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
    share_mode: str


class BIServer(ValidatedSQLModel, table=True):
    __tablename__ = "ts_bi_server"
    cluster_guid: str = Field(primary_key=True)
    sk_dummy: str = Field(primary_key=True)
    incident_id: str
    timestamp: dt.datetime
    url: str
    org_id: Optional[str]
    http_response_code: Optional[int]
    browser_type: Optional[str]
    browser_version: Optional[str]
    client_type: Optional[str]
    client_id: Optional[str]
    answer_book_guid: Optional[str]
    viz_id: Optional[str]
    user_id: Optional[str]
    user_action: Optional[str]
    query_text: Optional[str]
    response_size: Optional[int]
    latency_us: Optional[int]
    impressions: Optional[float]

    @pydantic.field_validator("timestamp", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)

    @pydantic.field_serializer("query_text")
    def escape_characters(self, query_text: Optional[str]) -> Optional[str]:
        """Ensure reserved characters are properly escaped."""
        if query_text is None:
            return query_text
        reserved_characters = ("\\",)

        for character in reserved_characters:
            query_text = query_text.replace(character, f"\\{character}")

        return query_text


METADATA_MODELS = [
    Cluster,
    Org,
    User,
    OrgMembership,
    Group,
    GroupPrivilege,
    GroupMembership,
    Tag,
    MetadataObject,
    MetadataColumn,
    ColumnSynonym,
    TaggedObject,
    DependentObject,
    SharingAccess,
]
BISERVER_MODELS = [BIServer]
