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

import unittest

from cst.model import DependencyTree, Table
from cst.io import DependencyTreeStdoutWriter


class TestDependencyTreeStdoutWriter(unittest.TestCase):
    """Tests (minimal) the dependency tree writer to stdout"""

    def test_write_pretty(self):
        """Tests writing using rich_print"""
        table1 = Table(guid="table1"); table1.name = "table1"
        table2 = Table(guid="table2"); table2.name = "table2"
        table3 = Table(guid="table3"); table3.name = "table3"
        table4 = Table(guid="table4"); table4.name = "table4"


        dt = DependencyTree()
        dt.add_table(table=table1)
        dt.add_table(table=table2)
        dt.add_table(table=table3)
        dt.add_table(table=table4)
        dt.add_table_dependencies(table_guid="table1", depends_on="table3", dependents="table4")
        dt.add_table_dependencies(table_guid="table2", depends_on="table4", dependents=["table3", "table4"])

        DependencyTreeStdoutWriter.write_dependency_tree(dt, rich_print=True)

