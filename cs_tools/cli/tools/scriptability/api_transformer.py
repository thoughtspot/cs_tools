from __future__ import annotations

from typing import Literal

from cs_tools import _types


def ts_metadata_object(data: list[_types.APIResult]) -> _types.TableRowsFormat:
    """Reshapes metadata/search -> searchable.models.MetadataObject."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        can_be_sage_enabled = result["metadata_type"] == "LOGICAL_TABLE"
        is_worksheetv2 = result["metadata_header"].get("worksheetVersion") == "V2"

        for org_id in result["metadata_header"].get("orgIds", None) or [0]:
            reshaped.append(
                {
                    "org_id": org_id,
                    "object_guid": result["metadata_id"],
                    "name": result["metadata_name"],
                    "description": result["metadata_header"].get("description", None),
                    "author_guid": result["metadata_header"]["author"],
                    "created": result["metadata_header"]["created"] / 1000,
                    "modified": result["metadata_header"]["modified"] / 1000,
                    "object_type": result["metadata_type"],
                    "object_subtype": "MODEL" if is_worksheetv2 else result["metadata_header"].get("type", None),
                    "data_source_guid": (result["metadata_detail"] or {}).get("dataSourceId", None),
                    "is_sage_enabled": (
                        not result["metadata_header"]["aiAnswerGenerationDisabled"] if can_be_sage_enabled else None
                    ),
                    "is_verified": result["metadata_header"].get("isVerified", False),
                    "is_version_controlled": result["metadata_header"].get("isVersioningEnabled", False),
                }
            )

    return reshaped


def tml_export_status(data: list[_types.APIResult]) -> _types.TableRowsFormat:
    """Reshapes metadata/tml/export or vcs/branches/commit -> scriptability.utils.TMLStatus."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        reshaped.append(
            {
                "operation": "EXPORT",
                "edoc": None,
                "metadata_guid": ...,
                "metadata_name": ...,
                "metadata_type": ...,
                "status": result.status,
                "message": response.error_message,
                "_raw": result,
            }
        )

    return reshaped


def tml_import_status(data: list[_types.APIResult], operation: Literal["VALIDATE", "IMPORT"]) -> _types.TableRowsFormat:
    """Reshapes metadata/tml/import or vcs/branches/deploy -> scriptability.utils.TMLStatus."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        reshaped.append(
            {
                "operation": operation,
                "edoc": None,
                "metadata_guid": ...,
                "metadata_name": ...,
                "metadata_type": ...,
                "status": result.status,
                "message": response.error_message,
                "_raw": result,
            }
        )

    return reshaped
