from __future__ import annotations

from typing import Any, Literal, Optional, Union
import datetime as dt
import json
import logging
import pathlib

import pydantic
import rich
import thoughtspot_tml

from cs_tools import _types

from . import api_transformer

_LOG = logging.getLogger(__name__)


def is_allowed_object(
    metadata_object: _types.APIResult,
    allowed_types: list[_types.MetadataObjectType],
    disallowed_system_users: list[_types.GUID],
) -> bool:
    """Determines if an object is allowed to be EXPORTED or IMPORTED."""
    if "TABLE" in allowed_types:
        allowed_types.append("ONE_TO_ONE_LOGICAL")
        allowed_types.append("USER_DEFINED")

    if "VIEW" in allowed_types:
        allowed_types.append("AGGR_WORKSHEET")

    if "MODEL" in allowed_types:
        allowed_types.append("WORKSHEET")

    #
    #
    #

    if metadata_object["author_guid"] in disallowed_system_users:
        return False

    if "ALL" in allowed_types:
        return True

    if metadata_object["object_type"] in allowed_types:
        return True

    if metadata_object["object_type"] == "LOGICAL_TABLE":
        return metadata_object["object_subtype"] in allowed_types

    return False


class MappingMetadataCheckpoint(pydantic.BaseModel):
    """Metadata about the export/import process."""

    by: str
    at: dt.datetime
    counter: int
    last_export: dt.datetime
    last_import: Optional[dt.datetime] = None

    @pydantic.field_serializer("at", "last_export", "last_import")
    @classmethod
    def serialize_datetime(self, value: dt.datetime) -> str:
        return value.isoformat()


class GUIDMappingInfo(pydantic.BaseModel):
    """Wrapper for guid mapping to make it easier to use."""

    metadata: dict[str, Any] = pydantic.Field(default={})
    mapping: dict[_types.GUID, Optional[_types.GUID]] = pydantic.Field(default={})
    additional_mapping: dict[str, str] = pydantic.Field(default={})

    _path: Optional[pathlib.Path] = None

    @classmethod
    def load(cls, path: Optional[pathlib.Path] = None) -> GUIDMappingInfo:
        """Load the GUID mapping info."""
        try:
            assert path is not None, "--> raise FileNotFoundError"
            info = cls.parse_obj(json.loads(path.read_text()))

        except (AssertionError, FileNotFoundError):
            info = cls()

        finally:
            info._path = path

        return info

    def disambiguate(self, tml: _types.TMLObject, delete_unmapped_guids: bool = True) -> _types.TMLObject:
        """Disambiguate an incoming TML object."""
        tml = thoughtspot_tml.utils.disambiguate(
            tml=tml,
            guid_mapping=self.mapping,
            remap_object_guid=True,
            delete_unmapped_guids=delete_unmapped_guids,
        )

        return tml

    def map_guid(self, *, old: _types.GUID, new: _types.GUID, disallow_overriding: bool = True) -> None:
        """Map a GUID."""
        if old not in self.mapping:
            _LOG.warning(f"Old GUID {old} not found in the mapping, setting anyway..")

        if (already_mapped := self.mapping.get(old, None)) is None:
            self.mapping[old] = new

        elif already_mapped == new:
            pass

        elif disallow_overriding:
            _LOG.warning(f"Old GUID {old} already mapped to {already_mapped}, skipping..")

        else:
            _LOG.warning(f"Old GUID {old} already mapped to {already_mapped}, overriding..")
            self.mapping[old] = new

    def save(self, new_path: Optional[pathlib.Path] = None) -> None:
        """Saves the GUID mappings."""
        if new_path is None and self._path is None:
            raise ValueError("No save path provided.")

        if new_path is not None:
            self._path = new_path

        assert self._path is not None, "This should be unreachable. GUIDMappingInfo requires a path."

        self._path.write_text(self.model_dump_json(indent=2))


class TMLStatus(pydantic.BaseModel):
    operation: Literal["EXPORT", "VALIDATE", "IMPORT"]
    edoc: Optional[str] = None
    metadata_guid: Optional[_types.GUID] = None
    metadata_name: Optional[str] = None
    metadata_type: Union[_types.UserFriendlyObjectType, Literal["WORKSHEET"], Literal["UNKNOWN"]] = "UNKNOWN"
    status: _types.TMLStatusCode
    message: Optional[str] = None
    _raw: dict

    @classmethod
    def from_api_response(cls, operation: Literal["EXPORT", "VALIDATE", "IMPORT"], data: _types.APIResult) -> TMLStatus:
        """Process the TML API response into a status."""
        if operation == "EXPORT":
            response = cls(
                operation=operation,
                edoc=data["edoc"],
                metadata_guid=data["info"]["id"],
                metadata_name=data["info"].get("name", "--"),
                metadata_type=data["info"].get("type", "UNKNOWN"),
                status=data["info"]["status"]["status_code"],
                message=data["info"]["status"].get("error_message", None),
                _raw=data,
            )

        if operation in ("VALIDATE", "IMPORT"):
            info = {
                "operation": operation,
                # metadata...
                "status": data["response"]["status"]["status_code"],
                "message": data["response"]["status"].get("error_message", None),
                "_raw": data,
            }

            if "header" in data["response"]:
                metadata_type = data["response"]["header"].get("type", data["response"]["header"]["metadata_type"])
                info["metadata_guid"] = data["response"]["header"]["id_guid"]
                info["metadata_name"] = data["response"]["header"]["name"]
                info["metadata_type"] = _types.lookup_metadata_type(metadata_type=metadata_type, mode="V1_TO_FRIENDLY")

            response = cls(**info)

            if response.metadata_guid and response.status == "ERROR":
                response.status = "WARNING"

        return response

    @pydantic.field_validator("metadata_type", mode="before")
    @classmethod
    def ensure_uppercase(cls, value: str) -> str:
        """Ensure the metadata type is uppercase."""
        return value.upper() if value is not None else value

    @pydantic.field_validator("message", mode="before")
    @classmethod
    def conform_newlines(cls, value: str) -> Optional[str]:
        """Some TML errors have <br/> tags instead of standard newlines."""
        if value is None:
            return None

        return value.replace("<br/>", "\n")

    @property
    def color(self) -> str:
        """Fetch the status color which represents the success of the tml response."""
        status_colors = {
            "ERROR": "fg-error",
            "WARNING": "fg-warn",
            "OK": "fg-success",
        }

        return status_colors[self.status]

    @property
    def emoji(self) -> str:
        """Fetch the status emoji which represents the success of the tml response."""
        # fmt: off
        status_emojis = {
            "ERROR": ":x:",                 # ❌
            "WARNING": ":rotating_light:",  # 🚨
            "OK": ":white_check_mark:",     # ✅
        }
        # fmt: on

        return status_emojis[self.status]


class TMLOperations:
    """Represents a job of TML operations."""

    def __init__(
        self,
        data: list[_types.APIResult],
        domain: str,
        op: Literal["EXPORT", "VALIDATE", "IMPORT"],
        policy: Optional[_types.TMLImportPolicy] = None,
    ):
        self.domain = domain
        self.operation = op
        self.policy = policy

        if op == "EXPORT":
            reshaped = api_transformer.tml_export_status(data)
        else:
            reshaped = api_transformer.tml_import_status(data, operation=op)

        self._statuses = [TMLStatus(**_) for _ in reshaped]

    @property
    def statuses(self) -> list[TMLStatus]:
        return self._statuses

    @property
    def can_map_guids(self) -> bool:
        """Determine if the statuses' GUIDs should be mapped."""
        if self.operation == "VALIDATE":
            return False

        if self.policy == "ALL_OR_NONE" and self.job_status != "OK":
            return False

        if self.policy == "PARTIAL" and any(_.status != "ERROR" for _ in self.statuses):
            return True

        return self.job_status != "ERROR"

    @property
    def job_status(self) -> _types.TMLStatusCode:
        """The aggregate status of the TML operation."""
        any_error = any(_.status == "ERROR" for _ in self.statuses)
        any_warn = any(_.status == "WARNING" for _ in self.statuses)

        if self.policy == "ALL_OR_NONE" and (any_error or any_warn):
            return "ERROR"

        if any_error:
            return "ERROR"

        if any_warn:
            return "WARNING"

        return "OK"

    @property
    def job_status_color(self) -> str:
        status_colors = {
            "ERROR": "fg-error",
            "WARNING": "fg-warn",
            "OK": "fg-success",
        }
        return status_colors[self.job_status]

    def __str__(self) -> str:
        """Represent the trimmed results as JSON."""
        results = [
            {
                "status": response.status,
                "metadata_type": response.metadata_type,
                "metadata_guid": response.metadata_guid,
                "metadata_name": response.metadata_name,
            }
            for response in self.statuses
        ]
        return json.dumps(results, indent=4)

    def __rich__(self) -> rich.console.ConsoleRenderable:
        """Generate a pretty table."""
        # fmt: off
        t = rich.table.Table(box=rich.box.SIMPLE_HEAD, row_styles=("dim", ""), width=150)
        t.add_column("",     width= 1 + 4, justify="center")  # LENGTH OF EMOJI         + 4 pad
        t.add_column("Type", width=10 + 4)  # LENGTH OF "CONNECTION" (the longest type) + 4 pad
        t.add_column("GUID", width=36 + 4)  # LENGTH OF A UUID                          + 4 pad
        t.add_column("Name", width=150 - 5 - 14 - 40, no_wrap=True)
        # fmt: on

        for response in self.statuses:
            t.add_row(response.emoji, response.metadata_type, response.metadata_guid, response.metadata_name)

        r = rich.panel.Panel(
            t,
            title="TML Status",
            subtitle=f"TML / {self.domain.upper()} / {self.operation}",
            subtitle_align="right",
            border_style=self.job_status_color,
        )

        return r
