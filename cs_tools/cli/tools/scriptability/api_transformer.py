from __future__ import annotations

from typing import Literal
import pathlib

from cs_tools import _types

from . import utils


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

    # RESPONSE TRANSFORMER FOR vcs/git/commit :: r.commited_files
    if _FROM_GIT_API_RESULTS := ("file_name" in next(iter(data), {})):
        for committed in data:
            # FORMAT: table/TS_DATA_SOURCE.2b7e3ebe-ee63-425c-824f-f09c0028e2b3.table.tml
            fp = pathlib.Path(committed["file_name"])

            metadata_guid = fp.suffixes[0].replace(".", "")
            metadata_name = fp.name.replace("".join(fp.suffixes), "")
            metadata_type = fp.suffixes[1].replace(".", "")

            # THESE ARE NOT SEMANTICALLY WARNINGS.....
            if _GOOFY_WARNING_STATUS := ("File not committed" in committed["status_message"]):
                status_code = "OK"
            else:
                status_code = committed["status_code"]

            reshaped.append(
                utils.TMLStatus(
                    operation="EXPORT",
                    edoc=None,
                    metadata_guid=metadata_guid,
                    metadata_name=metadata_name,
                    metadata_type=metadata_type,
                    status=status_code,
                    message=committed["status_message"],
                    _raw=committed,
                ).model_dump()
            )

    # RESPONSE TRANSFORMER FOR metadata/tml/export
    if _FROM_TML_API_RESULTS := ("info" in next(iter(data), {})):
        for result in data:
            reshaped.append(
                utils.TMLStatus(
                    operation="EXPORT",
                    edoc=result.get("edoc", None),  # None happens when we have an ERROR on export.
                    metadata_guid=result["info"]["id"],
                    metadata_name=result["info"].get("name", "--"),
                    metadata_type=result["info"].get("type", "UNKNOWN"),
                    status=result["info"]["status"]["status_code"],
                    message=result["info"]["status"].get("error_message", None),
                    _raw=result,
                ).model_dump()
            )

    return reshaped


def tml_import_status(data: list[_types.APIResult], operation: Literal["VALIDATE", "IMPORT"]) -> _types.TableRowsFormat:
    """Reshapes metadata/tml/import or vcs/branches/deploy -> scriptability.utils.TMLStatus."""
    reshaped: _types.TableRowsFormat = []

    if _FROM_GIT_API_RESULTS := ("file_name" in next(iter(data), {})):
        for deployed in data:
            fp = pathlib.Path(deployed["file_name"])

            # fp FORMAT .. table/TS_DATA_SOURCE.2b7e3ebe-ee63-425c-824f-f09c0028e2b3.table.tml
            try:
                metadata_guid = fp.suffixes[0].replace(".", "")
                metadata_name = fp.name.replace("".join(fp.suffixes), "")
                metadata_type = fp.suffixes[1].replace(".", "")

            # CONNECTIONS HAVE DIFFERENT FILE NAMES FOR ERRORS.
            # fp FORMAT ... 075ba586-76a3-4e38-8228-8ed20aecd990.tml
            except IndexError:
                metadata_guid = fp.name.replace("".join(fp.suffixes), "")
                metadata_name = "--"
                metadata_type = "CONNECTION"

            reshaped.append(
                utils.TMLStatus(
                    operation=operation,
                    edoc=None,  # Not possible on IMPORT.
                    metadata_guid=metadata_guid,
                    metadata_name=metadata_name,
                    metadata_type=metadata_type,
                    status=deployed["status_code"],
                    message=deployed["status_message"],
                    _raw=deployed,
                ).model_dump()
            )

    if _FROM_TML_API_RESULTS := ("response" in next(iter(data), {})):
        for result in data:
            info = {}

            if "header" in result["response"]:
                metadata_type = result["response"]["header"].get("type", result["response"]["header"]["metadata_type"])
                info["id"] = result["response"]["header"]["id_guid"]
                info["name"] = result["response"]["header"]["name"]
                info["type"] = _types.lookup_metadata_type(metadata_type=metadata_type, mode="V1_TO_FRIENDLY")

            # IF YOU CAN FETCH AN ID BACK FROM IMPORT, THEN SEMANTICALLY IT'S A WARNING.
            # (aka ERRORS BLOCK IMPORTS FROM HAPPENING)
            if info.get("id", None) is not None and result["response"]["status"]["status_code"] == "ERROR":
                status = "WARNING"
            else:
                status = result["response"]["status"]["status_code"]

            reshaped.append(
                utils.TMLStatus(
                    operation=operation,
                    edoc=None,  # Not possible on IMPORT.
                    metadata_guid=info.get("id", None),
                    metadata_name=info.get("name", "--"),
                    metadata_type=info.get("type", "UNKNOWN"),
                    status=status,
                    message=result["response"]["status"].get("error_message", None),
                    _raw=result,
                ).model_dump()
            )

    return reshaped
