"""
Copyright 2020 ThoughtSpot
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions
of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from collections.abc import Iterable
import copy
import json

from .util import eprint


class Table:
    """
    Represents a table or other table-like object in the system.
    Note that not all attributes of the call to get tables are included.
    """

    def __init__(self, guid=None, json_obj=None):
        """
        Creates an empty table object.  Note that the attributes match the names in the JSON description.
        :param guid: GUID of the table.
        :type guid: str
        :param json_obj: A string representing the JSON object.
        :type json_obj: str | dict
        """
        self.json_obj = None
        self.name = None                   # Name of the table.
        self.author = None                 # Author GUID.
        self.authorDisplayName = None      # Author display name.
        self.authorName = None             # Author name.
        self.databaseStripe = None         # Database name
        self.id = guid                     # GUID for the table.
        self.owner = None                  # Owner GUID.
        self.isDeleted = None              # If the table is deleted.
        self.isExternal = None             # True if is an external table, e.g. Snowflake.
        self.isHidden = None               # If the table is hidden.
        self.schemaStripe = None           # Schema name.
        self.type = None                   # Type: ONE_TO_ONE_LOGICAL, etc.

        if json_obj:
            self.populate_from_json(json_obj)

    def populate_from_json(self, json_obj):
        """
        Populates the attributes from a JSON object.
        :param json_obj: The JSON description of the table.  The object represents the table.
        :type json_obj: str | dict
        :return: None, populates the object from the JSON.
        """
        if isinstance(json_obj, str):  # allow strings to be passed in as well as parsed json.
            json_obj = json.loads(json_obj)

        try:
            self.json_obj = copy.copy(json_obj)

            for attr in self.__dict__:
                if attr in json_obj.keys():
                    self.__setattr__(attr, json_obj[attr])
        except KeyError as ke:
            eprint(f"Error parsing table JSON: {json_obj} {ke}")

    def __repr__(self):
        attrs = {attr: value for (attr, value) in self.__dict__.items() if not attr.startswith("_")}
        repr_str = f"{self.id} [name = {self.name}, type = {self.type}]: {attrs}"
        return repr_str

    def merge(self, other_table):
        """
        Merges properties from another table object.
        :param other_table: The other table to merge values from.
        :type other_table: Table
        :return: Nothing
        """
        for attr in self.__dict__:  # Only get the attributes this one cares about.
            if not attr.startswith("_"):  # don't copy protected / private values.
                if attr in other_table.__dict__.keys() and other_table.__dict__[attr] is not None:  # Don't copy None
                    self.__setattr__(attr, other_table.__dict__[attr])


class TableDependencies:
    """
    Defines dependencies for a given table.
    """
    def __init__(self, table_guid, depends_on=None, dependents=None):
        """
        Creates a dependency with details.  The table guid is required.
        :param table_guid: ID of the table for the dependencies.
        :type table_guid: str
        :param depends_on: The table guid(s) that this one depends on.
        :type depends_on: str | Iterable
        :param dependents: The table guid(s) that depend on this table.
        :type dependents: str | Iterable
        """
        assert table_guid
        assert not depends_on or (isinstance(depends_on, Iterable) or isinstance(depends_on, str))
        assert not dependents or (isinstance(dependents, Iterable) or isinstance(dependents, str))

        self.table_guid = table_guid
        self._depends_on = set()
        self._dependents = set()

        if depends_on:
            self.add_depends_on(depends_on=depends_on)

        if dependents:
            self.add_dependents(dependents=dependents)

    def add_depends_on(self, depends_on):
        """
        Adds a table or tables this one depends on.
        :param depends_on:  The tables (guids) that this one depends on.
        :type depends_on: str | Iterable
        :return: None
        """
        assert depends_on and (isinstance(depends_on, str) or isinstance(depends_on, Iterable))
        if isinstance(depends_on, str):
            self._depends_on.add(depends_on)
        else:
            self._depends_on.update(depends_on)

    def has_depends_on(self):
        """
        Returns true if the if there are tables that depend on this one.
        :return: True if the if there are tables that depend on this one.
        :rtype: bool
        """
        return len(self._depends_on) > 0

    def get_depends_on(self):
        """
        Returns (a copy of) the table guids this table depends on.
        :return: The table guids this table depends on.
        :rtype: set
        """
        return copy.copy(self._depends_on)

    def add_dependents(self, dependents):
        """
        Adds a table(s) that depend on this one.
        :param dependents: Table(s) that depend on this one.
        :type dependents: str | list of str
        :return: Nothing
        """
        assert dependents and (isinstance(dependents, str) or isinstance(dependents, Iterable))
        if isinstance(dependents, str):
            self._dependents.add(dependents)
        else:
            self._dependents.update(dependents)

    def has_dependents(self):
        """
        Returns true if the if there are tables that depend on this one.
        :return: True if the if there are tables that depend on this one.
        :rtype: bool
        """
        return len(self._dependents) > 0

    def get_dependents(self):
        """
        Returns (a copy of) the table guids that depend on this table.
        :return: The table guids this table depends on.
        :rtype: set
        """
        return copy.copy(self._dependents)


class DependencyTree:
    """
    Defines a dependency tree of tables that depend on other tables.
    The tree can be navigated in any direction, i.e. a list of tables can be retrieved and then find the tables that
    depend on it or that it depends on.
    """

    def __init__(self):
        """
        Create a dependency tree.
        """
        self._tables = {}  # mapping of table ids to tables.
        # mapping of table name to dependencies of the form
        #     { table_guid: TableDependencies }
        self._table_dependencies = {}

    def number_tables(self):
        """
        Returns the number of tables in the dependency tree.
        :return: The number of tables in the dependency tree.
        :rtype: int
        """
        return len(self._tables.keys())

    def add_table(self, table, depends_on=None, dependents=None):
        """
        Adds a table to the dependency tree.
        :param table: The table to add.
        :type table: Table
        :param depends_on: List of table guids that this one depends on.  No check is made to see if these tables have
        been added.
        :type depends_on: str | list of str
        :param dependents: List of table guids that depend on this one.  No check is made to see if these tables have
        been added.
        :type dependents: str | list of str
        :return: None
        """
        # Merge any tables that might be already in the tree.  This allows for updates to tables.
        table_to_add = self._tables.get(table.id, None)
        if table_to_add:
            table_to_add.merge(table)
        else:
            table_to_add = table

        self._tables[table_to_add.id] = table_to_add
        self.add_table_dependencies(table_guid=table_to_add.id, depends_on=depends_on, dependents=dependents)

    def get_table(self, table_guid):
        """
        Returns the table with the given GUID.
        :param table_guid: The GUID for the table to return.
        :type table_guid: str
        :return: The table or None
        :rtype: Table
        """
        return self._tables.get(table_guid, None)

    def add_table_dependencies(self, table_guid, depends_on=None, dependents=None):
        """
        Add dependencies for a given table.  These can be both tables that this one depends on or depend on it.
        :param table_guid: The table to add.
        :type table_guid: str
        :param depends_on: Table guids that this one depends on.  No check is made to see if these tables have
        been added.
        :type depends_on: str | Iterable
        :param dependents: Table guids that depend on this one.  No check is made to see if these tables have
        been added.
        :type dependents: str | Iterable
        :return: None
        """
        if not self._tables.get(table_guid, None):
            self._tables[table_guid] = Table(guid=table_guid)

        table_dependencies = self._table_dependencies.get(table_guid, None)
        if not table_dependencies:  # Add if it doesn't already exist.
            table_dependencies = TableDependencies(table_guid=table_guid, depends_on=depends_on, dependents=dependents)
            self._table_dependencies[table_guid] = table_dependencies

        # for both directions, make sure links go both ways if the related table has been added.
        # recursion could have been used, but only need to go one level deep.
        if depends_on:
            if isinstance(depends_on, str):
                depends_on = [depends_on]

            for d in depends_on:  # for each table this one depends on ...
                # ... create the table if needed.
                if not self._tables.get(d, None):
                    self._tables[d] = Table(guid=d)

                # ... get the table to add this one as a dependent
                depends_on_dependents = self._table_dependencies.get(d, None)
                # ... if not already there, add it
                if not depends_on_dependents:
                    depends_on_dependents = TableDependencies(table_guid=d)
                    self._table_dependencies[d] = depends_on_dependents

                # ... and then add the this table as a dependent.
                depends_on_dependents.add_dependents(dependents=table_guid)

        if dependents:
            if isinstance(dependents, str):
                dependents = [dependents]

            for d in dependents:  # for each table that depend on this one ...
                # ... create the table if needed.
                if not self._tables.get(d, None):
                    self._tables[d] = Table(guid=d)

                # ... get the table to add this one as a depends_on
                dependents_depends_on = self._table_dependencies.get(d, None)
                # ... if not already there, add it
                if not dependents_depends_on:
                    dependents_depends_on = TableDependencies(table_guid=d)
                    self._table_dependencies[d] = dependents_depends_on

                # ... and then add the this table as a being depended on.
                dependents_depends_on.add_depends_on(depends_on=table_guid)

    def get_all_tables(self):
        """
        Returns a copy of all the tables in the dependency tree.
        :return: A list of all the tables in the dependency tree.
        :rtype: list of Table
        """
        return [copy.deepcopy(table) for table in self._tables.values()]

    def get_table_ids(self):
        """
        Returns a set of all the table GUIDs.
        :return: A set of all the table GUIDs.
        :rtype: set of str
        """
        return set([id for id in self._tables.keys()])

    def get_root_tables(self):
        """
        Returns a list of the tables that don't depend on any other tables.  These tables are usually the base tables.
        :return: A list of tables that don't depend on other tables.  This is a copy of the original tables.
        :rtype: list of Table
        """
        return [copy.deepcopy(self._tables[table])
                for table in self._table_dependencies.keys()
                if not self._table_dependencies[table].has_depends_on()]

    def get_dependents(self, table_guid):
        """
        Returns a list of tables that depend on the given table or None if there are no tables that depend on that one.
        :param table_guid: The table guids to get the depencies of.
        :type table_guid: str
        :return: List of tables that depend on the given table or an empty list.
        :rtype: set of str
        """
        return (self._table_dependencies[table_guid].get_dependents()
                if table_guid in self._table_dependencies.keys() else [])

    def get_depends_on(self, table_guid):
        """
        Returns a list of tables that this one depends on.
        :param table_guid: Name of the table to find tables it depends on.
        :type table_guid: str
        :return: List of tables the one named depends on.
        :rtype: set of str
        """
        return (self._table_dependencies[table_guid].get_depends_on()
                if table_guid in self._table_dependencies.keys() else [])

    def extend(self, other_dependencies):
        """
        Adds the dependencies from the other dependency tree to this one.  Tables and dependencies are updated, but
        no tables or dependencies are removed.
        :param other_dependencies: The other dependencies to add.
        :type other_dependencies: DependencyTree
        :return: Nothing
        """
        for table in other_dependencies.get_all_tables():
            self.add_table(table=table,
                           depends_on=[table_id
                                       for table_id in other_dependencies.get_depends_on(table_guid=table.id)],
                           dependents=[table_id
                                       for table_id in other_dependencies.get_dependents(table_guid=table.id)])
