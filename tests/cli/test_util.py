import unittest

from cs_tools.cli.util import _TSDependentObject, TSDependencyTree


class TestTSDependencyTree(unittest.TestCase):

    def testNewDOWithoutDependents(self):
        """Tests creating a basic object with no dependencies."""
        dobj = _TSDependentObject("abcd")
        self.assertEqual(dobj.guid, "abcd")
        self.assertFalse(dobj.depends_on)
        self.assertEqual(dobj.level, 0)

    def testNewDOWithDependents(self):
        """Tests creating a basic object with dependencies and adding more."""
        dobj = _TSDependentObject("abcd", "defg")
        self.assertEqual(dobj.guid, "abcd")
        self.assertEqual(dobj.depends_on, {"defg"})
        self.assertEqual(dobj.level, 1)

        dobj.add_depends_on({"mnop", "qtrv"})
        self.assertEqual(dobj.depends_on, {"defg", "mnop", "qtrv"})

    def testNewDependencyTree(self):
        """Tests creating a new, empty tree."""
        dt = TSDependencyTree()
        self.assertEqual(0, len(dt))

    def testAddingDependencies(self):
        """
        Tests creating a tree and adding stuff to it, including setting levels.
        The structure is:
            obj1 - obj2, obj3 - level 4
            obj2 - obj4 - level 3
            obj3 - none - level 0
            obj4 - obj5, obj6, obj7 - 2
            obj5 - none - level 0
            obj6 - obj8 - level 1
            obj7 - none - level 0
            obj8 - none - level 0
        """
        dt = TSDependencyTree()
        dt.add_dependency("obj1", {"obj2", "obj3"})
        dt.add_dependency("obj2", {"obj4"})
        dt.add_dependency("obj3")
        dt.add_dependency("obj4", {"obj5", "obj6", "obj7"})
        dt.add_dependency("obj5")
        dt.add_dependency("obj6", "obj8")
        dt.add_dependency("obj7")
        dt.add_dependency("obj8")

        self.assertEqual(8, len(dt))
        self.assertEqual(4, dt._get_object_level("obj1"))
        self.assertEqual(3, dt._get_object_level("obj2"))
        self.assertEqual(0, dt._get_object_level("obj3"))
        self.assertEqual(2, dt._get_object_level("obj4"))
        self.assertEqual(0, dt._get_object_level("obj5"))
        self.assertEqual(1, dt._get_object_level("obj6"))
        self.assertEqual(0, dt._get_object_level("obj7"))
        self.assertEqual(0, dt._get_object_level("obj8"))

        print(dt)


