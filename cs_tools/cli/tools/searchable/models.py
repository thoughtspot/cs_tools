from typing import List, Optional
import datetime as dt
import logging

from sqlmodel import Field, SQLModel

log = logging.getLogger(__name__)


class User(SQLModel, table=True):
    __tablename__ = "ts_user"
    user_guid: str = Field(primary_key=True)
    username: str
    email: Optional[str]
    display_name: str
    sharing_visibility: str
    created: dt.datetime
    modified: dt.datetime
    user_type: str

    @classmethod
    def from_api_v1(cls, data) -> "User":
        """
        Takes input from /tspublic/v1/user.
        """
        data = {
            "user_guid": data["header"]["id"],
            "username": data["header"]["name"],
            "email": data["userContent"]["userProperties"].get("mail"),
            "display_name": data["header"]["displayName"],
            "sharing_visibility": data["visibility"],
            "created": data["header"]["created"],
            "modified": data["header"]["modified"],
            "user_type": data["type"],
        }
        return cls(**data)


class Group(SQLModel, table=True):
    __tablename__ = "ts_group"
    group_guid: str = Field(primary_key=True)
    group_name: str
    description: Optional[str]
    display_name: str
    sharing_visibility: str
    created: dt.datetime
    modified: dt.datetime
    group_type: str

    @classmethod
    def from_api_v1(cls, data) -> "Group":
        data = {
            "group_guid": data["header"]["id"],
            "group_name": data["header"]["name"],
            "description": data["header"].get("description"),
            "display_name": data["header"]["displayName"],
            "sharing_visibility": data["visibility"],
            "created": data["header"]["created"],
            "modified": data["header"]["modified"],
            "group_type": data["type"],
        }
        return cls(**data)


class GroupPrivilege(SQLModel, table=True):
    __tablename__ = "ts_group_privilege"
    group_guid: str = Field(primary_key=True, foreign_key="ts_group.group_guid")
    privilege: str = Field(primary_key=True)

    @classmethod
    def from_api_v1(cls, data) -> List["GroupPrivilege"]:
        return [cls(group_guid=data["header"]["id"], privilege=p) for p in data["privileges"]]


class XREFPrincipal(SQLModel, table=True):
    __tablename__ = "ts_xref_principal"
    principal_guid: str = Field(primary_key=True, foreign_key="ts_user.user_guid")
    group_guid: str = Field(primary_key=True, foreign_key="ts_group.group_guid")

    @classmethod
    def from_api_v1(cls, data) -> List["XREFPrincipal"]:
        return [cls(principal_guid=data["header"]["id"], group_guid=g) for g in data["assignedGroups"]]


class Tag(SQLModel, table=True):
    __tablename__ = "ts_tag"
    tag_guid: str = Field(primary_key=True)
    tag_name: str
    author_guid: str = Field(foreign_key="ts_user.user_guid")
    created: dt.datetime
    modified: dt.datetime
    color: Optional[str]

    @classmethod
    def from_api_v1(cls, data) -> List["Tag"]:
        if "clientState" not in data:
            log.warning(
                f"Tag '{data['name']}' ({data['id']}) is missing its color! There might be a problem with metadata in "
                f"your cluster."
            )

        return cls(
            tag_guid=data["id"],
            tag_name=data["name"],
            color=data.get("clientState", {}).get("color"),
            author_guid=data["author"],
            created=data["created"],
            modified=data["modified"],
        )


class MetadataObject(SQLModel, table=True):
    __tablename__ = "ts_metadata_object"
    object_guid: str = Field(primary_key=True)
    name: str
    description: Optional[str]
    author_guid: str = Field(foreign_key="ts_user.user_guid")
    created: dt.datetime
    modified: dt.datetime
    object_type: str

    @classmethod
    def from_api_v1(cls, data) -> "MetadataObject":
        data = {
            "object_guid": data["id"],
            "name": data["name"],
            "description": data.get("description"),
            "author_guid": data["author"],
            "created": data["created"],
            "modified": data["modified"],
            "object_type": data["type"],
        }
        return cls(**data)


class MetadataColumn(SQLModel, table=True):
    __tablename__ = "ts_metadata_column"
    column_guid: str = Field(primary_key=True)
    object_guid: str = Field(foreign_key="ts_metadata_object.object_guid")
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

    @classmethod
    def from_api_v1(cls, data) -> "MetadataColumn":
        return cls(**data)


class ColumnSynonym(SQLModel, table=True):
    __tablename__ = "ts_column_synonym"
    column_guid: str = Field(primary_key=True, foreign_key="ts_metadata_column.column_guid")
    synonym: str = Field(primary_key=True)

    @classmethod
    def from_api_v1(cls, data) -> "ColumnSynonym":
        return [cls(column_guid=data["column_guid"], synonym=s) for s in data.get("synonyms", [])]


class TaggedObject(SQLModel, table=True):
    __tablename__ = "ts_tagged_object"
    object_guid: str = Field(primary_key=True, foreign_key="ts_metadata_object.object_guid")
    tag_guid: str = Field(primary_key=True, foreign_key="ts_tag.tag_guid")

    @classmethod
    def from_api_v1(cls, data) -> List["TaggedObject"]:
        return [cls(object_guid=data["id"], tag_guid=t["id"]) for t in data["tags"]]


class DependentObject(SQLModel, table=True):
    __tablename__ = "ts_dependent_object"
    dependent_guid: str = Field(primary_key=True)
    column_guid: str = Field(primary_key=True, foreign_key="ts_metadata_column.column_guid")
    name: str
    description: Optional[str]
    author_guid: str = Field(foreign_key="ts_user.user_guid")
    created: dt.datetime
    modified: dt.datetime
    object_type: str

    @classmethod
    def from_api_v1(cls, data) -> "DependentObject":
        data = {
            "dependent_guid": data["id"],
            "column_guid": data["parent_guid"],
            "name": data["name"],
            "description": data.get("description"),
            "author_guid": data["author"],
            "created": data["created"],
            "modified": data["modified"],
            "object_type": data["type"],
        }
        return cls(**data)


class SharingAccess(SQLModel, table=True):
    __tablename__ = "ts_sharing_access"
    sk_dummy: str = Field(
        primary_key=True,
        sa_column_kwargs={"comment": "shared_to_* is a composite PK, but can be nullable, so we need a dummy"},
    )
    object_guid: str = Field(foreign_key="ts_metadata_object.object_guid")
    shared_to_user_guid: Optional[str] = Field(foreign_key="ts_user.user_guid")
    shared_to_group_guid: Optional[str] = Field(foreign_key="ts_group.group_guid")
    permission_type: str
    share_mode: str

    @classmethod
    def from_api_v1(cls, data) -> "SharingAccess":
        PK = (data["object_guid"], data.get("shared_to_user_guid", "NULL"), data.get("shared_to_group_guid", "NULL"))

        data = {
            "sk_dummy": "-".join(PK),
            "object_guid": data["object_guid"],
            "shared_to_user_guid": data.get("shared_to_user_guid", None),
            "shared_to_group_guid": data.get("shared_to_group_guid", None),
            "permission_type": data["permission_type"],
            "share_mode": data["share_mode"],
        }

        return cls(**data)


class BIServer(SQLModel, table=True):
    __tablename__ = "ts_bi_server"
    sk_dummy: str = Field(primary_key=True)
    incident_id: str
    timestamp: Optional[dt.datetime]
    url: str
    http_response_code: Optional[str]
    browser_type: Optional[str]
    browser_version: Optional[str]
    client_type: Optional[str]
    client_id: Optional[str]
    answer_book_guid: Optional[str] = Field(foreign_key="ts_metadata_object.object_guid")
    viz_id: Optional[str]
    user_id: Optional[str] = Field(foreign_key="ts_user.user_guid")
    user_action: Optional[str]
    query_text: Optional[str]
    response_size: Optional[int]
    latency_us: Optional[int]
    impressions: Optional[float]


METADATA_MODELS = [
    User,
    Group,
    GroupPrivilege,
    XREFPrincipal,
    Tag,
    MetadataObject,
    MetadataColumn,
    ColumnSynonym,
    TaggedObject,
    DependentObject,
    SharingAccess,
]
BISERVER_MODELS = [BIServer]
