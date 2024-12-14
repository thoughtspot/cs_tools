from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias, cast
import datetime as dt

from thoughtspot_tml._tml import TML  # noqa: F401

from cs_tools import _compat

# ==========
# Meta types
# ==========
ExitCode: TypeAlias = Literal[0, 1]

# ==========
# Data format types
# ==========
TableRowsFormat: TypeAlias = list[dict[str, dt.datetime | dt.date | bool | str | int | float | None]]
APIResult: TypeAlias = dict[str, Any]

# ==========
# ThoughtSpot common types
# ==========
GUID: TypeAlias = Annotated[str, "represented as a UUID"]
Name: TypeAlias = Annotated[str, "user-defined"]
ObjectIdentifier = GUID | Name
PrincipalIdentifier = GUID | Name


# fmt: off
InferredDataType = Literal[
    "VARCHAR", "CHAR",
    "DOUBLE", "FLOAT",
    "BOOL",
    "INT32", "INT64",
    "DATE", "DATE_TIME", "TIMESTAMP",
]
# fmt: on


# ==========
# ThoughtSpot API input types
# ==========
APIObjectType = Literal[
    "LIVEBOARD", "ANSWER", "LOGICAL_TABLE", "LOGICAL_COLUMN", "CONNECTION", "TAG", "USER", "USER_GROUP",
    "LOGICAL_RELATIONSHIP", "INSGIHT_SPEC"
]
PrincipalType = Literal["USER", "USER_GROUP"]
ImportPolicy = Literal["PARTIAL", "ALL_OR_NONE", "VALIDATE_ONLY", "PARTIAL_OBJECTS_ONLY"]
ShareType = Literal["DEFINED", "EFFECTIVE"]
ShareMode = Literal["NO_ACCESS", "READ_ONLY", "MODIFY"]


class GroupPrivilege(_compat.StrEnum):
    """Represents privileges which can be assigned to Groups or Roles."""

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


class Principal(_compat.TypedDict):
    """Represents a User or Group."""

    identifier: PrincipalIdentifier
    type: PrincipalType | None


def lookup_api_type(metadata_type: str) -> APIObjectType:
    """Determine the APIObjectType based on the V1 enum."""
    ENUM_TO_TYPE_MAPPING = {
        "PINBOARD_ANSWER_BOOK": "LIVEBOARD",
        "QUESTION_ANSWER_BOOK": "ANSWER",
    }

    return cast(APIObjectType, ENUM_TO_TYPE_MAPPING.get(metadata_type, metadata_type))
