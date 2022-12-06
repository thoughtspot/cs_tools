"""Contains useful classes and methods for scriptability."""
import copy
import pathlib
from typing import Callable, List

from thoughtspot_tml.types import TMLObject
from thoughtspot_tml.utils import disambiguate as _disambiguate, EnvironmentGUIDMapper
from cs_tools.data.enums import GUID, MetadataObject


class GUIDMapping:
    """Wrapper for guid mapping to make it easier to use."""

    def __init__(self, from_env: str, to_env: str, path: pathlib.Path):
        """
        Creates a new GUIDMapping
        :param from_env: The from environment name.
        :param to_env: The to environment name.
        :param path: The file to read from and/or save to.
        """
        self.from_env: str = from_env
        self.to_env: str = to_env
        self.path: pathlib.Path = path

        # forcing names to lower to make consistent.
        transformer: Callable[[str], str] = str.lower
        if path.exists():
            self.guid_mapper = EnvironmentGUIDMapper.read(path=path, environment_transformer=transformer)
        else:
            self.guid_mapper: EnvironmentGUIDMapper = EnvironmentGUIDMapper(environment_transformer=transformer)

    def get_mapped_guid(self, from_guid):
        """Returns the guid mapping"""
        # guid_mapper.get() -> { DEV: guid1, PROD: guid2, ... }
        # get the GUID or return the original
        return self.guid_mapper.get(from_guid, default={}).get(self.to_env, from_guid)

    def set_mapped_guid(self, from_guid, to_guid):
        """Sets the guid mapping from the old to the new."""
        self.guid_mapper[from_guid] = (self.from_env, from_guid)
        self.guid_mapper[from_guid] = (self.to_env, to_guid)

    def disambiguate(self, tml: TMLObject, delete_unmapped: bool = False):
        """
        Replaces source GUIDs with target.
        :param tml: A TLM object to replace GUIDs for.
        :param delete_unmapped: If true, unmapped GUIDs will be removed.
        """
        # self.guid_mapper.generate_map(DEV, PROD) # =>  {envt_A_guid1: envt_B_guid2 , .... }
        mapper = self.guid_mapper.generate_mapping(self.from_env, self.to_env)
        _disambiguate(tml=tml, guid_mapping=mapper, delete_unmapped_guid=delete_unmapped)

    def save(self):
        """Saves the GUID mappings."""
        self.guid_mapper.save(path=self.path, info={"test": True})


class TMLFileBundle:
    """
    Bundles file information with TML to make it easier to track and log.
    """

    def __init__(self, file: pathlib.Path, tml: TMLObject):
        """
        Creates a new TMLFileBundle
        :param file: A path to the TML file.
        :param tml: The TML from the file.  This may be modified.
        """
        self.file = file
        self.tml = tml


class MetadataTypeList:
    """
    Mapping of metadata types to GUIDs.  Makes it easy to work with APIs that require both.
    """

    def __init__(self):
        """
        Creates a new metadata type list.
        """
        self._mapping = {}  # key is the metadata type and the value is a list of GUIDs.

    def add(self, metadata_type: MetadataObject, guid: GUID) -> None:
        """
        Adds a GUID and type mapping.
        :param metadata_type: The type of metadata.
        :param guid: The GUID for the metadata.
        """
        ids = self._mapping.get(metadata_type, None)
        if not ids:
            ids = []
            self._mapping[metadata_type] = ids

        ids.append(guid)

    def remove(self, metadata_type: str, guid) -> bool:
        """
        Removes the GUID for given type from the object.
        :param metadata_type: The type ot remove.
        :param guid: The GUID to remove for the type.
        :return: True if removed.  False if not in the list for that type.
        """
        ids = self._mapping.get(metadata_type, None)
        if guid in ids:
            ids.remove(guid)
            if not self._mapping.get(metadata_type, None):  # clear it out if there are no more GUIDs for the type.
                self._mapping.pop(metadata_type)

            return True

        return False

    def types(self) -> List[str]:
        """
        Returns a list of the metadata types that are in the list.
        """
        return copy.copy(list(self._mapping.keys()))

    def guids_for_type(self, metadata_type: str) -> List[GUID]:
        """
        Returns the GUIDs for the given metadata type or an empty list.
        :param metadata_type: The metadata type to get.
        """
        if metadata_type in self._mapping.keys():
            return copy.copy(self._mapping[metadata_type])
        else:
            return []

    def is_empty(self) -> bool:
        """
        Returns True if the mappings are empty.
        """
        return len(self._mapping) <= 0

    def __str__(self):
        """Returns a nice string for printing."""
        s = "{"
        for mtype in self._mapping.keys():
            s += f'{mtype.value}: [{", ".join(self._mapping[mtype])}], '

        if s.endswith(", "):
            s = s[0: len(s) - 2]  # strip out the last ,
        s += "}"

        return s


def strip_blanks(inp: List[str]) -> List[str]:
    """Strips blank out of a list."""
    return [e for e in inp if e]


def get_guid_from_filename(fn: str) -> GUID:
    """
    Returns a GUID from the file name.  Assumes the filename is of the form <guid>.<type>.tml.  Anything before
    the first period is assumed to be the GUID.
    :param fn: The name of the file (not the full path, just the file).
    :return: The GUID part of the file.
    """
    return fn.split('.')[0]
