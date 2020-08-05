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

import json
import unittest

from cst.model import Table, TableDependencies, DependencyTree


class TestTable(unittest.TestCase):
    """Tests the model classes."""

    def test_create_table(self):
        """Tests creating a table."""
        table = Table()
        self.assertIsNone(table.name)

        table = Table(guid="test_table")
        self.assertEqual(table.id, "test_table")

    def test_create_table_from_json(self):
        """Tests creating a table object from JSON."""
        table_str = """{"id": "5d51637f-174b-4a63-9de9-1b21a1e1fc18",
                        "indexVersion": 2299,
                        "generationNum": 2299,
                        "name": "test_table",
                        "author": "0f0dd0f7-7411-4195-a4aa-0dc6b58413c9", 
                        "authorName": "su",
                        "authorDisplayName": "Administrator Super-User",
                        "created": 1591666251401,
                        "modified": 1591666251556,
                        "modifiedBy": "0f0dd0f7-7411-4195-a4aa-0dc6b58413c9",
                        "owner": "5d51637f-174b-4a63-9de9-1b21a1e1fc18",
                        "isDeleted": "False",
                        "isHidden": "False",
                        "schemaStripe": "falcon_default_schema",
                        "databaseStripe": "test_database",
                        "tags": [{"id": "d5e097ec-79f6-4c4a-93ce-ee44de6ebf03",
                        "indexVersion": 2279,
                        "generationNum": 2279,
                        "name": "Test Table",
                        "author": "59481331-ee53-42be-a548-bd87be6ddd4a",
                        "created": 1591666328903,
                        "modified": 1591666329125,
                        "modifiedBy": "59481331-ee53-42be-a548-bd87be6ddd4a",
                        "owner": "d5e097ec-79f6-4c4a-93ce-ee44de6ebf03",
                        "isDeleted": "False",
                        "isHidden": "False",
                        "clientState": {"color": "#c82b78"},
                        "tags": [],
                        "isExternal": "False"}],
                        "type": "ONE_TO_ONE_LOGICAL",
                        "isExternal": "False"}"""
        table_obj = json.loads(table_str)

        t = Table()
        self.assertTrue(not t.json_obj)
        self.assertTrue(not t.author)

        t = Table(json_obj=table_str)
        print(t)
        self.assertEqual(table_obj, t.json_obj)

        self.assertEqual("0f0dd0f7-7411-4195-a4aa-0dc6b58413c9", t.author)
        self.assertEqual("Administrator Super-User", t.authorDisplayName)
        self.assertEqual("su", t.authorName)
        self.assertEqual("test_database", t.databaseStripe)
        self.assertEqual("5d51637f-174b-4a63-9de9-1b21a1e1fc18", t.id)
        self.assertEqual("False", t.isDeleted)
        self.assertEqual("False", t.isHidden)
        self.assertEqual("test_table", t.name)
        self.assertEqual("5d51637f-174b-4a63-9de9-1b21a1e1fc18", t.owner)
        self.assertEqual("falcon_default_schema", t.schemaStripe)
        self.assertEqual("ONE_TO_ONE_LOGICAL", t.type)

    def test_merge_table(self):
        """Tests merging attributes from one table into another."""
        t1, t2 = Table(), Table()

        t1.name = "table 1"
        t1.isHidden = "False"

        t2.id = "123"         # new value
        t2.isHidden = "True"  # overwrite value

        t1.merge(t2)
        self.assertEqual("table 1", t1.name)
        self.assertEqual("True", t1.isHidden)
        self.assertEqual("123", t1.id)


class TestTableDependencies(unittest.TestCase):
    """Tests the TableDependencies class."""

    def test_table_dependencies_empty(self):
        """Tests the TableDependencies class."""
        td = TableDependencies("table_1")
        self.assertTrue(not td.get_depends_on())
        self.assertTrue(not td.get_dependents())

        self.assertFalse(td.has_dependents())
        self.assertFalse(td.has_depends_on())

        td.add_dependents(dependents="table_a")
        td.add_dependents(dependents="table_a")  # verify only gets added once.
        td.add_dependents(dependents=["table_b", "table_c"])

        td.add_depends_on("table_x")
        td.add_depends_on("table_x")  # verify only gets added once.
        td.add_depends_on("table_y")

        self.assertTrue(td.has_dependents())
        self.assertTrue(td.has_depends_on())

        dependents = td.get_dependents()
        self.assertEqual(3, len(dependents))
        self.assertTrue("table_a" in dependents)
        self.assertTrue("table_b" in dependents)
        self.assertTrue("table_c" in dependents)

        depends_on = td.get_depends_on()
        self.assertEqual(2, len(depends_on))
        self.assertTrue("table_x" in depends_on)
        self.assertTrue("table_y" in depends_on)

    def test_table_dependencies(self):
        """Tests the TableDependencies class."""
        td = TableDependencies("table_1", depends_on=["table_x", "table_y", "table_z"],
                               dependents=["table_a", "table_b"])

        dependents = td.get_dependents()
        self.assertEqual(2, len(dependents))
        self.assertTrue("table_a" in dependents)
        self.assertTrue("table_b" in dependents)

        depends_on = td.get_depends_on()
        self.assertEqual(3, len(depends_on))
        self.assertTrue("table_x" in depends_on)
        self.assertTrue("table_y" in depends_on)
        self.assertTrue("table_z" in depends_on)


class TestDependencyTree(unittest.TestCase):
    """
    Tests the DependencyTree class.
    """

    def test_create_tree(self):
        """Tests creating a dependency tree."""
        dt = DependencyTree()

        # Verify calls without data will return empty lists.
        self.assertEqual(dt.get_all_tables(), [])
        self.assertEqual(dt.get_root_tables(), [])
        self.assertEqual(dt.get_depends_on(table_guid="unknown"), [])
        self.assertEqual(dt.get_dependents(table_guid="unknown"), [])

    def test_add_tables(self):
        """Tests adding tables and no dependencies to the dependency tree."""
        dt = DependencyTree()
        tables = [Table(guid="table1"), Table(guid="table2"), Table(guid="table3")]
        table_ids = [t.id for t in tables]
        for t in tables:
            dt.add_table(table=t)

        # Verify all tables are in the tree.
        tables_ids_in_dt = [t.id for t in dt.get_all_tables()]
        self.assertTrue(all(x in tables_ids_in_dt for x in table_ids))

        # Verify all tables are also root tables (no dependents).
        tables_ids_in_dt = [t.id for t in dt.get_root_tables()]
        self.assertTrue(all(x in tables_ids_in_dt for x in table_ids))

    def test_set_dependencies(self):
        """Test setting and getting dependencies."""
        dt = DependencyTree()

        dt.add_table_dependencies(table_guid="table1")  # No dependents or depends_on.
        # Dependents, but no depends_on.
        dt.add_table_dependencies(table_guid="table2", dependents=["object_2_1", "object_2_2"])
        # Depends_on, but no dependents.
        dt.add_table_dependencies(table_guid="table3", depends_on=["object_3_1", "object_3_2"])
        # Both depends_on and dependents.
        dt.add_table_dependencies(table_guid="table4", depends_on="object_4_1", dependents="object_4_2")
        # Create with both via add_table.
        dt.add_table(table=Table(guid="table5"), depends_on="object_5_1", dependents="object_5_2")

        root_tables = dt.get_root_tables()
        self.assertEqual(6, len(root_tables))
        tables_ids_in_dt = [t.id for t in dt.get_root_tables()]
        self.assertTrue(all(x in tables_ids_in_dt for x in ["table1", "table2", "object_3_1", "object_3_2",
                                                            "object_4_1", "object_5_1"]))

        depends_on = dt.get_depends_on(table_guid="table2")
        self.assertEqual(0, len(depends_on))
        depends_on = dt.get_depends_on(table_guid="table3")
        self.assertEqual(2, len(depends_on))
        self.assertTrue(all(x in depends_on for x in ["object_3_1", "object_3_2"]))

        dependents = dt.get_dependents(table_guid="table3")
        self.assertEqual(0, len(dependents))
        dependents = dt.get_dependents(table_guid="table2")
        self.assertEqual(2, len(dependents))
        self.assertTrue(all(x in dependents for x in ["object_2_1", "object_2_2"]))

        # Checking that the objects got set correctly.
        depends_on = dt.get_depends_on(table_guid="object_2_1")
        self.assertEqual({"table2"}, depends_on)
        dependents = dt.get_dependents(table_guid="object_2_1")
        self.assertEqual(set(), dependents)

    def test_dependency_tree_extend(self):
        """Tests extending a dependency tree."""
        dt1 = DependencyTree()
        dt1.add_table(table=Table(guid="table1"), dependents="object1.1", depends_on="object1.2")

        dt2 = DependencyTree()
        dt2.add_table(table=Table(guid="table1"), dependents="object1.3")
        dt2.add_table(table=Table(guid="table2"), dependents="object2.1", depends_on="object2.2")

        dt1.extend(dt2)

        tables = [table.id for table in dt1.get_all_tables()]
        self.assertTrue(all(x in tables for x in ["table1", "table2"]))

        depends_on = dt1.get_depends_on(table_guid="table1")
        self.assertEqual({"object1.2"}, depends_on)
        dependents = dt1.get_dependents(table_guid="table1")
        self.assertEqual({"object1.1", "object1.3"}, dependents)

        # adding due to bug where dependencies were getting the parent's dependencies.
        depends_on = dt1.get_depends_on(table_guid="object1.1")
        self.assertEqual({"table1"}, depends_on)
        dependents = dt1.get_dependents(table_guid="object1.1")
        self.assertEqual(set(), dependents)

    def test_get_ids(self):
        """Tests getting the ids for tables."""
        dt = DependencyTree()
        dt.add_table(Table(guid="table1"))
        dt.add_table(Table(guid="table2"))
        dt.add_table(Table(guid="table3"))

        ids = dt.get_table_ids()
        self.assertTrue(all(x in ids for x in ["table1", "table2", "table3"]))


if __name__ == '__main__':
    unittest.main()
