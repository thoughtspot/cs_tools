from __future__ import annotations

from typing import Any, Literal, Optional, Union
import datetime as dt
import json
import pathlib

import pydantic
import rich

from cs_tools import _types


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

    # def disambiguate(self, tml: TMLObject, delete_unmapped_guids: bool = False) -> None:
    #     """
    #     Replaces source GUIDs with target.
    #     """
    #     # self.guid_mapper.generate_map(DEV, PROD) # =>  {envt_A_guid1: envt_B_guid2 , .... }
    #     mapper = self.guid_mapper.generate_mapping(self.source, self.dest)

    #     _disambiguate(
    #         tml=tml,
    #         guid_mapping=mapper,
    #         remap_object_guid=self.remap_object_guid,
    #         delete_unmapped_guids=delete_unmapped_guids,
    #     )

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
    metadata_guid: _types.GUID
    metadata_name: str
    metadata_type: Union[_types.UserFriendlyObjectType, Literal["WORKSHEET"], Literal["UNKNOWN"]] = "UNKNOWN"
    status: _types.TMLStatusCode
    message: Optional[str] = None
    _raw: dict

    @classmethod
    def from_api_response(cls, operation: Literal["EXPORT", "VALIDATE", "IMPORT"], data: _types.APIResult) -> TMLStatus:
        """..."""
        response = cls(
            operation=operation,
            edoc=data["edoc"],
            metadata_guid=data["info"]["id"],
            metadata_name=data["info"]["name"],
            metadata_type=data["info"]["type"],
            status=data["info"]["status"]["status_code"],
            message=data["info"]["status"].get("error_message", None),
            _raw=data,
        )
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

    def __init__(self, data: list[_types.APIResult], domain: str, op: Literal["EXPORT", "VALIDATE", "IMPORT"]):
        self.data = data
        self.domain = domain
        self.operation = op
        self._statuses = [TMLStatus.from_api_response(operation=op, data=_) for _ in self.data]

    @property
    def statuses(self) -> list[TMLStatus]:
        """Get the statuses of the TML operation."""
        return self._statuses

    @property
    def job_status(self) -> _types.TMLStatusCode:
        """The aggregate status of the TML operation."""
        if any(_.status == "ERROR" for _ in self.statuses):
            return "ERROR"
        if any(_.status == "WARNING" for _ in self.statuses):
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
