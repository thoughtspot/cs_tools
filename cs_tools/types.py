from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import datetime as dt
import typing
import enum
import uuid

from thoughtspot_tml.types import TMLObject, ConnectionMetadata
import dateutil

GUID = typing.cast(uuid.UUID, str)


# ======================================================================================================================
# REST API V1 literals
#
#   These are predefined enumerated sets values, determined by ThoughtSpot. The member name is a human-readable variant
#   or what is show in the ThoughtSpot UI, while the member value is the API contract value.
# ======================================================================================================================

class FormatType(enum.Enum):
    records = "FULL"
    values = "COMPACT"


class MetadataObjectType(enum.Enum):
    logical_table = "LOGICAL_TABLE"
    logical_column = "LOGICAL_COLUMN"
    logical_relationship = "LOGICAL_RELATIONSHIP"
    saved_answer = "QUESTION_ANSWER_BOOK"
    pinboard = "PINBOARD_ANSWER_BOOK"
    liveboard = "PINBOARD_ANSWER_BOOK"
    connection = "DATA_SOURCE"
    user = "USER"
    group = "USER_GROUP"


class MetadataObjectSubtype(enum.Enum):
    system_table = "ONE_TO_ONE_LOGICAL"
    worksheet = "WORKSHEET"
    csv_upload = "USER_DEFINED"
    thoughtspot_view = "AGGR_WORKSHEET"
    sql_view = "SQL_VIEW"
    formula = "FORMULA"
    calendar_type = "CALENDAR_TYPE"
    calendar = "CALENDAR_TABLE"


class MetadataCategory(enum.Enum):
    all = "ALL"
    my = "MY"
    favorite = "FAVORITE"
    requested = "REQUESTED"


class SortOrder(enum.Enum):
    default = "DEFAULT"
    name = "NAME"
    display_name = "DISPLAY_NAME"
    author_name = "AUTHOR"
    created = "CREATED"
    modified = "MODIFIED"


class ConnectionType(enum.Enum):
    azure = 'RDBMS_AZURE_SQL_DATAWAREHOUSE'
    big_query = 'RDBMS_GCP_BIGQUERY'
    databricks = 'RDBMS_DATABRICKS'
    oracle_adw = 'RDBMS_ORACLE_ADW'
    presto = 'RDBMS_PRESTO'
    redshift = 'RDBMS_REDSHIFT'
    sap_hana = 'RDBMS_SAP_HANA'
    snowflake = 'RDBMS_SNOWFLAKE'


class TMLType(enum.Enum):
    yaml = "YAML"
    json = "JSON"


class TMLImportPolicy(enum.Enum):
    all_or_none = "ALL_OR_NONE"
    partial = "PARTIAL"
    validate = "VALIDATE_ONLY"


class PermissionType(enum.Enum):
    inherited = "EFFECTIVE"
    explicit = "DEFINED"


class ShareModeAccessLevel(enum.Enum):
    no_access = "NO_ACCESS"
    can_view = "READ_ONLY"
    can_modify = "MODIFY"


class GroupPrivilege(enum.Enum):
    innate = 'AUTHORING'
    can_administer_thoughtspot = 'ADMINISTRATION'
    can_upload_user_data = 'USERDATAUPLOADING'
    can_download_data = 'DATADOWNLOADING'
    has_developer_privilege = 'DEVELOPER'
    can_share_with_all_users = 'SHAREWITHALL'
    can_manage_data = 'DATAMANAGEMENT'
    can_use_experimental_features = 'EXPERIMENTALFEATUREPRIVILEG'
    can_invoke_custom_r_analysis = 'RANALYSIS'
    can_manage_sync = 'SYNCMANAGEMENT'
    can_schedule_for_others = 'JOBSCHEDULING'
    has_spotiq_privilege = 'A3ANALYSIS'
    can_administer_and_bypass_rls = 'BYPASSRLS'
    cannot_create_or_delete_pinboards = 'DISABLE_PINBOARD_CREATION'


# ======================================================================================================================
# REST API V1 input parameter types
# ======================================================================================================================

class UserProfile(typing.TypedDict):
    # GET: callosum/v1/tspublic/v1/user
    ...


class SecurityPrincipal(typing.TypedDict):
    # GET: callosum/v1/tspublic/v1/user/list
    ...


# ======================================================================================================================
# CS Tools Internal types
# ======================================================================================================================

@dataclass
class ThoughtSpotPlatform:
    version: str
    deployment: str  # one of: cloud, software
    url: str
    timezone: str
    cluster_name: str
    cluster_id: str

    def __post_init__(self):
        self.tz: dt.timezone = dateutil.tz.gettz(self.timezone)

    @classmethod
    def from_api_v1_session_info(cls, info: dict[str, Any]) -> ThoughtSpotPlatform:
        config_info = info.get("configInfo")

        data = {
            'version': info['releaseVersion'],
            'deployment': 'cloud' if config_info['isSaas'] else 'software',
            'url': config_info.get('emailConfig', {}).get('welcomeEmailConfig', {}).get('getStartedLink', "NOT SET"),
            'timezone': info['timezone'],
            'cluster_name': config_info['selfClusterName'],
            'cluster_id': config_info['selfClusterId'],
        }

        return cls(**data)


@dataclass
class LoggedInUser:
    guid: GUID
    username: str
    display_name: str
    email: str
    privileges: list[GroupPrivilege]

    @classmethod
    def from_api_v1_session_info(cls, info: dict[str, Any]) -> LoggedInUser:
        data = {
            'guid': info['userGUID'],
            'name': info['userName'],
            'display_name': info['userDisplayName'],
            'email': info['userEmail'],
            'privileges': info['privileges']
        }

        return cls(**data)
