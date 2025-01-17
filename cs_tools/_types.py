from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union, cast
import datetime as dt

from thoughtspot_tml._tml import TML  # noqa: F401

from cs_tools import _compat

# ==========
# Meta types
# ==========
ExitCode: _compat.TypeAlias = Literal[0, 1]

# ==========
# Data format types
# ==========
TableRowsFormat: _compat.TypeAlias = list[dict[str, Union[dt.datetime, dt.date, bool, str, int, float, None]]]
APIResult: _compat.TypeAlias = dict[str, Any]

# ==========
# CS Tools types
# ==========
AuthContext = Literal["BEARER_TOKEN", "TRUSTED_AUTH", "BASIC", "NONE"]

# ==========
# ThoughtSpot common types
# ==========
GUID: _compat.TypeAlias = Annotated[str, "represented as a UUID"]
Name: _compat.TypeAlias = Annotated[str, "user-defined"]
OrgIdentifier = Union[int, Name]
ObjectIdentifier = Union[GUID, Name]
PrincipalIdentifier = Union[GUID, Name]


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
# fmt: off
APIObjectType = Literal[
    "CONNECTION",
    "LOGICAL_TABLE",
    "LIVEBOARD", "ANSWER",
    "LOGICAL_COLUMN",
    "TAG",
    "USER", "USER_GROUP",
    "LOGICAL_RELATIONSHIP", "INSGIHT_SPEC",
]
UserFriendlyObjectType = Literal[
    "CONNECTION",
    "TABLE", "VIEW", "SQL_VIEW", "MODEL",
    "LIVEBOARD", "ANSWER",
]
# fmt: on
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
    type: Optional[PrincipalType]


class TQLQueryContext(_compat.TypedDict):
    """Represents a database context for a TQL session."""

    # NOTE: https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_inputoutput_structure

    database: str
    schema: str
    server_schema_version: int


def lookup_api_type(
    metadata_type: str, *, mode: Literal["V1", "FRIENDLY"] = "V1", strict: bool = False
) -> APIObjectType:
    """
    Determine the APIObjectType based on a standard metadata type.

    If strict is True, raise a KeyError if the metadata type is unknown.
    """
    FRIENDLY_TO_API_TYPE_MAPPING = {
        "CONNECTION": "CONNECTION",
        "TABLE": "LOGICAL_TABLE",
        "VIEW": "LOGICAL_TABLE",
        "SQL_VIEW": "LOGICAL_TABLE",
        "MODEL": "LOGICAL_TABLE",
        "LIVEBOARD": "LIVEBOARD",
        "ANSWER": "ANSWER",
    }
    V1_ENUM_TO_API_TYPE_MAPPING = {
        "PINBOARD_ANSWER_BOOK": "LIVEBOARD",
        "QUESTION_ANSWER_BOOK": "ANSWER",
    }

    mapping = FRIENDLY_TO_API_TYPE_MAPPING if mode == "FRIENDLY" else V1_ENUM_TO_API_TYPE_MAPPING
    api_type = mapping.get(metadata_type.upper(), None)

    if api_type is None:
        if strict:
            raise KeyError(f"Unknown metadata type: {metadata_type}")
        api_type = metadata_type

    return cast(APIObjectType, api_type)
