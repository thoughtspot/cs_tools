from __future__ import annotations

from typing import Any, List, Dict
import logging
import typing
import uuid
import re

from thoughtspot_tml.types import ConnectionMetadata, TMLObject
import pendulum
import pydantic

from cs_tools._compat import StrEnum, TypedDict

log = logging.getLogger(__name__)
GUID = typing.cast(uuid.UUID, str)


# ======================================================================================================================
# REST API V1 literals
#
#   These are predefined enumerated sets values, determined by ThoughtSpot. The member name is a human-readable variant
#   or what is show in the ThoughtSpot UI, while the member value is the API contract value.
# ======================================================================================================================


class FormatType(StrEnum):
    records = "FULL"
    values = "COMPACT"


class MetadataObjectType(StrEnum):
    logical_table = "LOGICAL_TABLE"
    logical_column = "LOGICAL_COLUMN"
    logical_relationship = "LOGICAL_RELATIONSHIP"
    saved_answer = "QUESTION_ANSWER_BOOK"
    pinboard = "PINBOARD_ANSWER_BOOK"
    liveboard = "PINBOARD_ANSWER_BOOK"
    connection = "DATA_SOURCE"
    user = "USER"
    group = "USER_GROUP"


class MetadataObjectSubtype(StrEnum):
    system_table = "ONE_TO_ONE_LOGICAL"
    worksheet = "WORKSHEET"
    csv_upload = "USER_DEFINED"
    thoughtspot_view = "AGGR_WORKSHEET"
    sql_view = "SQL_VIEW"
    formula = "FORMULA"
    calendar_type = "CALENDAR_TYPE"
    calendar = "CALENDAR_TABLE"


class MetadataCategory(StrEnum):
    all = "ALL"
    my = "MY"
    favorite = "FAVORITE"
    requested = "REQUESTED"


class SortOrder(StrEnum):
    default = "DEFAULT"
    name = "NAME"
    display_name = "DISPLAY_NAME"
    author_name = "AUTHOR"
    created = "CREATED"
    modified = "MODIFIED"


class ConnectionType(StrEnum):
    azure = "RDBMS_AZURE_SQL_DATAWAREHOUSE"
    big_query = "RDBMS_GCP_BIGQUERY"
    databricks = "RDBMS_DATABRICKS"
    oracle_adw = "RDBMS_ORACLE_ADW"
    presto = "RDBMS_PRESTO"
    redshift = "RDBMS_REDSHIFT"
    sap_hana = "RDBMS_SAP_HANA"
    snowflake = "RDBMS_SNOWFLAKE"


class TMLType(StrEnum):
    yaml = "YAML"
    json = "JSON"


class TMLImportPolicy(StrEnum):
    all_or_none = "ALL_OR_NONE"
    partial = "PARTIAL"
    validate = "VALIDATE_ONLY"


class PermissionType(StrEnum):
    inherited = "EFFECTIVE"
    explicit = "DEFINED"


class ShareModeAccessLevel(StrEnum):
    no_access = "NO_ACCESS"
    can_view = "READ_ONLY"
    can_modify = "MODIFY"


class GroupPrivilege(StrEnum):
    innate = "AUTHORING"
    can_administer_thoughtspot = "ADMINISTRATION"
    can_upload_user_data = "USERDATAUPLOADING"
    can_download_data = "DATADOWNLOADING"
    has_developer_privilege = "DEVELOPER"
    can_share_with_all_users = "SHAREWITHALL"
    can_manage_data = "DATAMANAGEMENT"
    can_use_experimental_features = "EXPERIMENTALFEATUREPRIVILEG"
    can_invoke_custom_r_analysis = "RANALYSIS"
    can_manage_sync = "SYNCMANAGEMENT"
    can_schedule_for_others = "JOBSCHEDULING"
    has_spotiq_privilege = "A3ANALYSIS"
    can_administer_and_bypass_rls = "BYPASSRLS"
    cannot_create_or_delete_pinboards = "DISABLE_PINBOARD_CREATION"


# ======================================================================================================================
# REST API V1 input parameter types
# ======================================================================================================================


class UserProfile(TypedDict):
    # GET: callosum/v1/tspublic/v1/user
    ...


class SecurityPrincipal(TypedDict):
    # GET: callosum/v1/tspublic/v1/user/list
    ...


# ======================================================================================================================
# CS Tools Middleware types
# ======================================================================================================================


class TMLSupportedContent(StrEnum):
    connection = "DATA_SOURCE"
    table = "LOGICAL_TABLE"
    view = "LOGICAL_TABLE"
    sql_view = "LOGICAL_TABLE"
    sqlview = "LOGICAL_TABLE"
    worksheet = "LOGICAL_TABLE"
    pinboard = "PINBOARD_ANSWER_BOOK"
    liveboard = "PINBOARD_ANSWER_BOOK"
    answer = "QUESTION_ANSWER_BOOK"

    @classmethod
    def from_friendly_type(cls, friendly_type: str) -> TMLSupportedContent:
        return cls[friendly_type]


# ======================================================================================================================
# CS Tools Middleware output types
# ======================================================================================================================


RecordsFormat = list[dict[str, Any]]
# records are typically a metadata header fragment, but not always.
#
# [
#     {
#         "id": str,
#         "name": str,
#         "description": None | str,
#         "type": str,
#         ...
#     },
#     ...
# ]


class TMLAPIResponse(pydantic.BaseModel):
    guid: str
    metadata_object_type: str
    tml_type_name: str
    name: str
    status_code: str
    error_messages: List[str] = None
    _full_response: Any = None

    @pydantic.validator("status_code", pre=True)
    def _one_of(cls, status: str) -> str:
        ALLOWED = ("OK", "WARNING", "ERROR")

        if status.upper() not in ALLOWED:
            allowed = ", ".join(f"'{s}'" for s in ALLOWED)
            raise ValueError(f"'status_code' must be one of {allowed}, got '{status}'")

        return status.lower()

    @pydantic.validator("error_messages", pre=True)
    def _parse_errors(cls, error_string: str) -> List[str]:
        if error_string is None:
            return []

        return [e.strip() for e in re.split("<br/>|\n", error_string) if e.strip()]

    @property
    def is_success(self) -> bool:
        return self.status_code == "OK"

    @property
    def is_error(self) -> bool:
        return self.status_code == "ERROR"


# ======================================================================================================================
# CS Tools Internal types
# ======================================================================================================================


class ThoughtSpotPlatform(pydantic.BaseModel):
    version: str
    deployment: str
    url: str
    timezone: pendulum._Timezone
    cluster_name: str
    cluster_id: str

    @pydantic.validator("deployment", pre=True)
    def _one_of(cls, deployment: str) -> str:
        if deployment.lower() not in ("software", "cloud"):
            raise ValueError(f"'deployment' must be one of 'software' or 'cloud', got '{deployment}'")
        return deployment.lower()

    @pydantic.validator("timezone", pre=True)
    def _get_tz(cls, tz_name: str) -> pendulum._Timezone:
        timezone = pendulum.timezone(tz_name)

        if timezone is None:
            log.warning(f"could not retrieve timezone for '{tz_name}'")

        return timezone

    @classmethod
    def from_api_v1_session_info(cls, info: dict[str, Any]) -> ThoughtSpotPlatform:
        config_info = info.get("configInfo")

        data = {
            "version": info["releaseVersion"],
            "deployment": "cloud" if config_info["isSaas"] else "software",
            "url": config_info.get("emailConfig", {}).get("welcomeEmailConfig", {}).get("getStartedLink", "NOT SET"),
            "timezone": info["timezone"],
            "cluster_name": config_info["selfClusterName"],
            "cluster_id": config_info["selfClusterId"],
        }

        return cls(**data)

    class Config:
        arbitrary_types_allowed = True


class LoggedInUser(pydantic.BaseModel):
    guid: GUID
    username: str
    display_name: str
    email: str
    privileges: List[GroupPrivilege]

    @classmethod
    def from_api_v1_session_info(cls, info: Dict[str, Any]) -> LoggedInUser:
        data = {
            "guid": info["userGUID"],
            "username": info["userName"],
            "display_name": info["userDisplayName"],
            "email": info["userEmail"],
            "privileges": info["privileges"],
        }

        return cls(**data)

    class Config:
        arbitrary_types_allowed = True
