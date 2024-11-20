from __future__ import annotations

from typing import Literal, TypeAlias
import uuid

from cs_tools import _compat

# ==========
# Meta types
# ==========
CSToolsStatusCode: TypeAlias = Literal[0, 1]

# ==========
# Data format types
# ==========
TableRowsFormat: TypeAlias = list[dict[str, str]]

# ==========
# ThoughtSpot common types
# ==========
GUID: TypeAlias = uuid.UUID
Name: TypeAlias = str
ObjectIdentifier = GUID | Name

ImportPolicy = Literal["PARTIAL", "ALL_OR_NONE", "VALIDATE_ONLY", "PARTIAL_OBJECTS_ONLY"]
MetadataObject = Literal["LOGICAL_TABLE", "ANSWER", "LIVEBOARD"]
SharingAccess = Literal["DEFINED", "EFFECTIVE"]

# fmt: off
InferredDataType = Literal[
    "VARCHAR", "CHAR",
    "DOUBLE", "FLOAT",
    "BOOL",
    "INT32", "INT64",
    "DATE", "DATE_TIME", "TIMESTAMP",
]
# fmt: on


class GroupPrivilege(_compat.StrEnum):
    innate = "AUTHORING"
    can_administer_thoughtspot = "ADMINISTRATION"
    can_upload_user_data = "USERDATAUPLOADING"
    can_download_data = "DATADOWNLOADING"
    has_developer_privilege = "DEVELOPER"
    can_share_with_all_users = "SHAREWITHALL"
    can_manage_data = "DATAMANAGEMENT"
    can_use_experimental_features = "EXPERIMENTALFEATUREPRIVILEGE"
    can_invoke_custom_r_analysis = "RANALYSIS"
    can_manage_sync = "SYNCMANAGEMENT"
    can_preview_thoughtspot_sage = "PREVIEW_THOUGHTSPOT_SAGE"
    can_schedule_for_others = "JOBSCHEDULING"
    has_spotiq_privilege = "A3ANALYSIS"
    can_administer_and_bypass_rls = "BYPASSRLS"
    cannot_create_or_delete_pinboards = "DISABLE_PINBOARD_CREATION"
    can_verify_liveboard = "LIVEBOARD_VERIFIER"
    can_invoke_third_party_spotiq_analysis = "THIRDPARTY_ANALYSIS"
