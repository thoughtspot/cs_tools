"""Contains useful classes and methods for scriptability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NewType
import pathlib

from thoughtspot_tml import Connection
from thoughtspot_tml.types import TMLObject
from thoughtspot_tml.utils import (
    EnvironmentGUIDMapper as Mapper,
    disambiguate as _disambiguate,
)

if TYPE_CHECKING:
    from cs_tools.types import GUID

EnvName = NewType("EnvName", str)


class GUIDMapping:
    """
        Wrapper for guid mapping to make it easier to use.

        Attributes
        ----------
    from_env : str
          the source environment

        to_env : str
          the target environment

        filepath : pathlib.Path
          path to the mapping object

        remap_object_guid : bool, default = True
          whether to remap the top-level tml.guid
    """

    def __init__(self, source: EnvName, dest: EnvName, path: pathlib.Path, remap_object_guid: bool = True):
        self.source: str = source
        self.dest: str = dest
        self.path: pathlib.Path = path
        self.remap_object_guid = remap_object_guid
        self.guid_mapper = Mapper.read(path, str.lower) if path.exists() else Mapper(str.lower)

    def get_mapped_guid(self, from_guid: GUID) -> GUID:
        """
        Get the mapped guid.
        """
        # { DEV: guid1, PROD: guid2, ... }
        all_envts_from_guid = self.guid_mapper.get(from_guid, default={})
        return all_envts_from_guid.get(self.dest, from_guid)

    def set_mapped_guid(self, from_guid: GUID, to_guid: GUID) -> None:
        """
        Sets the guid mapping from the old to the new.

        You have to set both to make sure both are in the file.
        """
        self.guid_mapper[from_guid] = (self.source, from_guid)
        self.guid_mapper[from_guid] = (self.dest, to_guid)

    def set_mapped_guids(self, from_guids: list[GUID], to_guids: list[GUID]) -> None:
        """
        Sets a set of mapped GUIDs.
        """
        for _ in range(len(from_guids)):
            self.set_mapped_guid(from_guids[_], to_guids[_])

    def generate_mapping(self, from_environment: str, to_environment: str) -> dict[GUID, GUID]:
        return self.guid_mapper.generate_mapping(from_environment, to_environment)

    def disambiguate(self, tml: TMLObject, delete_unmapped_guids: bool = False) -> None:
        """
        Replaces source GUIDs with target.
        """
        # self.guid_mapper.generate_map(DEV, PROD) # =>  {envt_A_guid1: envt_B_guid2 , .... }
        mapper = self.guid_mapper.generate_mapping(self.source, self.dest)

        _disambiguate(
            tml=tml,
            guid_mapping=mapper,
            remap_object_guid=self.remap_object_guid,
            delete_unmapped_guids=delete_unmapped_guids,
        )

    def save(self) -> None:
        """
        Saves the GUID mappings.
        """
        self.guid_mapper.save(path=self.path, info={"generated-by": "cs_tools/scriptability"})


@dataclass
class TMLFile:
    """
    Combines file information with TML.
    """

    filepath: pathlib.Path
    tml: TMLObject

    @property
    def is_connection(self) -> bool:
        return isinstance(self.tml, Connection)


def strip_blanks(inp: list[str]) -> list[str]:
    """Strips blank out of a list."""
    return [e for e in inp if e]
