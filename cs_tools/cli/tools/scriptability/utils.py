from __future__ import annotations

from typing import Literal
import json

import rich

from cs_tools import _types

# """Contains useful classes and methods for scriptability."""

# from __future__ import annotations

# from dataclasses import dataclass
# from typing import TYPE_CHECKING, NewType
# import pathlib

# from thoughtspot_tml import Connection
# from thoughtspot_tml.types import TMLObject
# from thoughtspot_tml.utils import (
#     EnvironmentGUIDMapper as Mapper,
#     disambiguate as _disambiguate,
# )

# if TYPE_CHECKING:
#     from cs_tools.types import GUID

# EnvName = NewType("EnvName", str)


# class GUIDMapping:
#     """
#         Wrapper for guid mapping to make it easier to use.

#         Attributes
#         ----------
#     from_env : str
#           the source environment

#         to_env : str
#           the target environment

#         filepath : pathlib.Path
#           path to the mapping object

#         remap_object_guid : bool, default = True
#           whether to remap the top-level tml.guid
#     """

#     def __init__(self, source: EnvName, dest: EnvName, path: pathlib.Path, remap_object_guid: bool = True):
#         self.source: str = source
#         self.dest: str = dest
#         self.path: pathlib.Path = path
#         self.remap_object_guid = remap_object_guid
#         self.guid_mapper = Mapper.read(path, str.lower) if path.exists() else Mapper(str.lower)

#     def get_mapped_guid(self, from_guid: GUID) -> GUID:
#         """
#         Get the mapped guid.
#         """
#         # { DEV: guid1, PROD: guid2, ... }
#         all_envts_from_guid = self.guid_mapper.get(from_guid, default={})
#         return all_envts_from_guid.get(self.dest, from_guid)

#     def set_mapped_guid(self, from_guid: GUID, to_guid: GUID) -> None:
#         """
#         Sets the guid mapping from the old to the new.

#         You have to set both to make sure both are in the file.
#         """
#         self.guid_mapper[from_guid] = (self.source, from_guid)
#         self.guid_mapper[from_guid] = (self.dest, to_guid)

#     def set_mapped_guids(self, from_guids: list[GUID], to_guids: list[GUID]) -> None:
#         """
#         Sets a set of mapped GUIDs.
#         """
#         for _ in range(len(from_guids)):
#             self.set_mapped_guid(from_guids[_], to_guids[_])

#     def generate_mapping(self, from_environment: str, to_environment: str) -> dict[GUID, GUID]:
#         return self.guid_mapper.generate_mapping(from_environment, to_environment)

#     def disambiguate(self, tml: TMLObject, delete_unmapped_guids: bool = False) -> None:
#         """
#         Replaces source GUIDs with target.
#         """
#         # self.guid_mapper.generate_map(DEV, PROD) # =>  {envt_A_guid1: envt_B_guid2 , .... }
#         mapper = self.guid_mapper.generate_mapping(self.source, self.dest)

#         _disambiguate(
#             tml=tml,
#             guid_mapping=mapper,
#             remap_object_guid=self.remap_object_guid,
#             delete_unmapped_guids=delete_unmapped_guids,
#         )

#     def save(self) -> None:
#         """
#         Saves the GUID mappings.
#         """
#         self.guid_mapper.save(path=self.path, info={"generated-by": "cs_tools/scriptability"})


# @dataclass
# class TMLFile:
#     """
#     Combines file information with TML.
#     """

#     filepath: pathlib.Path
#     tml: TMLObject

#     @property
#     def is_connection(self) -> bool:
#         return isinstance(self.tml, Connection)


# def strip_blanks(inp: list[str]) -> list[str]:
#     """Strips blank out of a list."""
#     return [e for e in inp if e]


class TMLOperations:
    """Represents a job of TML operations."""

    def __init__(self, data: list[_types.APIResult], domain: str, op: Literal["EXPORT", "VALIDATE", "IMPORT"]):
        self.data = data
        self.domain = domain
        self.operation = op

    @property
    def job_status(self) -> _types.TMLStatusCode:
        """What is the aggregate status of the TML operation."""
        if any(_["info"]["status"]["status_code"] == "ERROR" for _ in self.data):
            return "ERROR"
        if any(_["info"]["status"]["status_code"] == "WARNING" for _ in self.data):
            return "WARNING"
        return "OK"

    def _make_status_emoji(self, status: _types.TMLStatusCode) -> str:
        """Fetch the status emoji which represents the success of the tml response."""
        status_emojis = {
            "ERROR": ":x:",  # ❌
            "WARNING": ":rotating_light:",  # 🚨
            "OK": ":white_check_mark:",  # ✅
        }

        return status_emojis.get(status, ":white_check_mark:")

    def _make_status_color(self, status: _types.TMLStatusCode) -> str:
        """Fetch the status emoji which represents the success of the tml response."""
        status_colors = {
            "ERROR": "fg-error",
            "WARNING": "fg-warn",
            "OK": "fg-success",
        }

        return status_colors.get(status, "fg-warn")

    def __str__(self) -> str:
        """Represent the trimmed results as JSON."""
        results = [
            {
                "status": tml_response["info"]["status"]["status_code"],
                "metadata_type": tml_response["info"].get("type", "UNKNOWN").upper(),
                "metadata_guid": tml_response["info"]["id"],
                "metadata_name": tml_response["info"]["name"],
            }
            for tml_response in self.data
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

        for tml_response in self.data:
            t.add_row(
                self._make_status_emoji(tml_response["info"]["status"]["status_code"]),
                tml_response["info"].get("type", "UNKNOWN").upper(),
                tml_response["info"]["id"],
                tml_response["info"]["name"],
            )

        r = rich.panel.Panel(
            t,
            title="TML Status",
            subtitle=f"TML / {self.domain.upper()} / {self.operation}",
            subtitle_align="right",
            border_style=self._make_status_color(self.job_status),
        )

        return r
