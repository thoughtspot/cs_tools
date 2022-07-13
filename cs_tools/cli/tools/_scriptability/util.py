"""Contains useful classes and methods for scriptability."""
import copy
import pathlib
from typing import List

from thoughtspot_tml.tml import TML
from cs_tools.data.enums import GUID


class TMLFileBundle:
    """
    Bundles file information with TML to make it easier to track and log.
    """

    def __init__(self, file: pathlib.Path, tml: TML):
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

    def add(self, metadata_type: str, guid: GUID) -> None:
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
