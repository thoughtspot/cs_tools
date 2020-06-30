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

from cst.api import DependencyFinder
from cst.io import DependencyTreeStdoutWriter

TS_URL = "https://tstest"
TS_USER = "tsadmin"
TS_PASSWORD = "admin"


class TestDependencyFinder(unittest.TestCase):
    """Tests the DependencyFinder class."""

    def test_get_all_tables(self):
        """Tests getting all tables."""
        # TODO Add better test.  Right now this tests against a general environment that may not have known tables.
        df = DependencyFinder(tsurl=TS_URL, username=TS_USER, password=TS_PASSWORD, disable_ssl=True)
        tables = df.get_all_tables()
        self.assertTrue(len(tables) > 0)

    def test_get_dependencies(self):
        """
        Tests getting dependencies for tables.
        TODO Add better tests.  Testing against a generic environment, so only really handles the calls.
        """
        df = DependencyFinder(tsurl=TS_URL, username=TS_USER, password=TS_PASSWORD, disable_ssl=True)
        dt = df.get_dependencies_for_all_tables()
        self.assertTrue(dt.number_tables() > 0)

    def test_get_dependencies_except_ts(self):
        """Tests getting dependencies with ignore_ts flag set to True."""
        df = DependencyFinder(tsurl=TS_URL, username=TS_USER, password=TS_PASSWORD, disable_ssl=True)
        dt = df.get_dependencies_for_all_tables(ignore_ts=True)
        no_ts_tables = True
        for table in dt.get_all_tables():
            if table.name.startswith("TS:"):
                no_ts_tables = False
        self.assertTrue(no_ts_tables)
