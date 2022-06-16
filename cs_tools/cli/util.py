import base64
import logging
import pathlib
from typing import Dict, Set, Union

from cs_tools.data.enums import GUID

log = logging.getLogger(__name__)


def base64_to_file(string: str, *, filepath: pathlib.Path) -> None:
    """
    Write a base64-encoded string to file.

    Parameters
    ----------
    string : str
      base64-encoded data

    filepath : pathlib.Path
      where to write the data encoded in string
    """
    # DEV NOTE:
    #
    #   This is a utility which takes data from an internal API and
    #   converts it to a base64 string, sometimes that data isn't
    #   well-formatted since we often ask the API to do something it
    #   isn't strictly designed to do.
    #
    #   The missing_padding check might not be necessary once the TML
    #   apis are public.
    #
    #   further reading: https://stackoverflow.com/a/9807138
    #
    add_padding = len(string) % 4

    if add_padding:
        log.warning(
            f'adding {add_padding} padding characters to meet the required octect '
            f'length for {filepath}'
        )
        string += '=' * add_padding

    with pathlib.Path(filepath).open(mode='wb') as file:
        file.write(base64.b64decode(string))


"""
Dependency trees and related classes are used to manage dependencies of objects in ThoughtSpot based on GUIDs
"""


class _TSDependentObject:
    """
    Defines a dependent object and the things it depends on.  A calculated level is also contained and possibly updated.
    """

    def __init__(self, guid: GUID, depends_on: Union[Set[GUID], GUID, None] = None):
        """
        Creates a new dependent object with optional objects on which it depends.  These objects can be added to.
        :param guid: The GUID for the object.
        :param depends_on: The items this object depends on.
        """
        # handle set vs single
        dpl = depends_on
        if depends_on and not isinstance(depends_on, set):
            dpl = {depends_on}

        self.guid = guid
        self.depends_on = dpl.copy() if dpl else {}
        self.level = 1 if depends_on else 0  # 0 is the base level for dependents, so if it depends on others, it's 1.

    def add_depends_on(self, depends_on: Union[Set[GUID], GUID, None]) -> None:
        """
        Adds a GUID for an object(s) this one depends on.
        :param depends_on: The GUID of the object this one depends on.
        """
        dpl = depends_on
        if dpl and not isinstance(dpl, set):
            dpl = {depends_on}

        if dpl:  # don't add if it's empty.
            self.depends_on = self.depends_on | dpl

    def __str__(self):
        """Simple string representation."""
        return f"{self.guid} (level: {self.level}) depends on [{','.join(self.depends_on)}]"


class TSDependencyTree:
    """
    A dependency tree manages TS dependencies of objects.  So an object can have a dependency and then that one can
    have dependencies, etc. until the final node (leaf) with no dependents is contained.  Note that circular
    dependencies are not possible in ThoughtSpot, so an object can't depend on an object that also depends on that one.
    """

    # Each item has an object ID (GUID) and the IDs of the things it depends on.

    def __init__(self):
        """
        Creates a new tree with a root.
        """
        self._objects: Dict[GUID, _TSDependentObject] = {}
        self._levels = []  # levels from 0 to ....  Used to iterate by level.

    def __len__(self):
        return len(self._objects.keys())

    def add_dependency(self, guid: GUID, depends_on: Union[Set[GUID], GUID] = None) -> None:
        """
        Adds a dependency to the object.
        :param guid: GUID for an item that depends on things.
        :param depends_on: GUID the item depends on.  If None, then it has no dependencies.
        """
        # get or create the object.
        dependent_object = self._objects.get(guid)
        if not dependent_object:
            dependent_object = _TSDependentObject(guid=guid, depends_on=depends_on)
            self._objects[guid] = dependent_object

        # add the dependencies
        dependent_object.add_depends_on(depends_on=depends_on)
        self._update_levels()

    def _update_levels(self) -> None:
        """
        Updates the levels of the items based on the tree of dependents.  The leaf nodes always have the highest level.
        This could be expensive if there are a lot of objects because it checks the entire tree.  However, it's not
        expected that there will be a lot of objects.
        TODO figure out a more efficient way to update the levels.
        """
        for guid in self._objects.keys():
            self._objects[guid].level = self._get_object_level(guid)

        # now, update the levels, so we can iterate over them cleanly.  Creating a dict and then converting back to
        # list since the objects won't be in order.
        levels = {}
        max_level = 0
        for _ in self._objects.values():
            lvl = levels.get(_.level)
            if not lvl:
                levels[_.level] = [_.guid]
            else:
                levels[_.level].append(_.guid)
            max_level = max(max_level, _.level)

        self._levels = []  # reset each time.
        for _ in range(max_level + 1):  # convert to a list of lists based on depth.  Load from 0 up.
            self._levels.append(levels.get(_, []))

    def _get_object_level(self, guid: GUID) -> int:
        """
        Returns the level of the object, level 0 being for any object that
        :param guid: The guid of the object to calculate the level of.
        """
        obj = self._objects.get(guid)
        level = 0
        if obj:
            for _ in obj.depends_on:
                level = max(level, self._get_object_level(_) + 1)

        return level

    @property
    def levels(self):
        """
        Returns an iterator over the levels.  Each element is a list of objects.
        """
        return self._levels.copy()

    def __str__(self) -> str:
        """Gives a nice string representation of the object levels."""
        res = ""
        lvl = 0
        for _ in self._levels:
            res += f"{lvl}: {_}\n"
            lvl += 1

        return res
