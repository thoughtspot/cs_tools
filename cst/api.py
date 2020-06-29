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

import argparse
import json
import logging
import requests

from .io import DependencyTreeStdoutWriter
from .model import DependencyTree, Table, TableDependencies
from .util import eprint, printif


def api_call(f):
    """
    Makes sure to try to call login if not already logged in.  This only works for classes that extend BaseApiInterface.
    :param f: Function to decorate.
    :return: A new callable method that will try to login first.
    """

    def wrap(self, *args, **kwargs):
        """
        Verifies that the user is logged in and then makes the call.  Assumes something will be returned.
        :param self:  Instance calling a method.
        :param args:  Place arguments.
        :param kwargs: Key word arguments.
        :return: Whatever the wrapped method returns.
        """
        if not self.is_authenticated():
            self.login()
        return f(self, *args, **kwargs)

    return wrap


def get_cluster_args():
    """
    Returns a common parser for anything calling TS that can be extended.  Includes the following arguments:
    - tsurl - URL to call.
    - username - User to call the API on behalf of.  Defaults to tsadmin.
    - password - Password for the user.  Defaults to tsadmin password.
    - disable_ssl - Should ignore missing SSL certs?  Defaults to true.
    :return: A base parser that can be added to and used to pars arguments.
    :rtype argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--tsurl", help="URL to ThoughtSpot, e.g. https://myserver")
    parser.add_argument("--username", default='tsadmin', help="Name of the user to log in as.")
    parser.add_argument("--password", default='admin', help="Password for login of the user to log in as.")
    parser.add_argument("--disable_ssl", action="store_true", help="Will ignore SSL errors.", default=True)
    return parser


# Declare the service URLs to use for API calls.
# Note that "tsurl" is the value that will be replaced with the server URL.
BASE_SERVICE_URL = "{tsurl}/callosum/v1"
LOGIN_URL = "/tspublic/v1/session/login"


class BaseApiInterface:
    """
    Provides basic support for calling the ThoughtSpot APIs, particularly for logging in.
    """
    SERVER_URL = "{tsurl}/callosum/v1"

    def __init__(self, tsurl, username, password, disable_ssl=False):
        """
        Creates a new sync object and logs into ThoughtSpot
        :param tsurl: Root ThoughtSpot URL, e.g. http://some-company.com/
        :type tsurl: str
        :param username: Name of the admin login to use.
        :type username: str
        :param password: Password for admin login.
        :type password: str
        :param disable_ssl: If true, then disable SSL for calls.
        password for all users.  This can be significantly faster than individual passwords.
        """
        assert tsurl and username and password
        self.tsurl = tsurl
        self.username = username
        self.password = password
        self.cookies = None
        self.session = requests.Session()
        self.disable_ssl = disable_ssl
        if disable_ssl:
            self.session.verify = False
        self.session.headers = {"X-Requested-By": "ThoughtSpot"}

    def login(self):
        """
        Log into the ThoughtSpot server.
        """
        url = self.format_url(LOGIN_URL)
        response = self.session.post(
            url, data={"username": self.username, "password": self.password}
        )

        if response.status_code == 204:
            self.cookies = response.cookies
            logging.info(f"Successfully logged in as {self.username}")
        else:
            logging.error(f"Failed to log in as {self.username}")
            raise requests.ConnectionError(
                f"Error logging in to TS ({response.status_code})",
                response.text,
            )

    def is_authenticated(self):
        """
        Returns true if the session is authenticated
        :return: True if the session is authenticated.
        :rtype: bool
        """
        return self.cookies is not None

    def format_url(self, url):
        """
        Returns a URL that has the correct server.
        :param url: The URL template to add the server to.
        :type url: str
        :return: A URL that has the correct server info.
        :rtype: str
        """
        url = BaseApiInterface.SERVER_URL + url
        return url.format(tsurl=self.tsurl)


class DependencyFinder(BaseApiInterface):
    """
    Supports finding dependencies on different objects.
    """

    def __init__(self, tsurl, username, password, disable_ssl=False):
        """
        Creates a dependency finder for the given cluster with the login info provided.
        :param tsurl: The URL to the server, e.g. https://thoughtspot.mycompany.com
        :type tsurl: str
        :param username: Name of a user with admin privileges to call the APIs.
        :type username: str
        :param password: The password for the user.
        :type password: str
        :param disable_ssl: Disable SSL warnings for calls if set to True.
        :type disable_ssl: bool
        """
        super().__init__(tsurl, username, password, disable_ssl)
        self._checked_table_ids = set()

    def get_complete_endpoint(self, endpoint):
        """
        Returns a complete path to call.
        :param endpoint: The path to the web service endpoint.
        :type endpoint: str
        :return: The full path for the web service call.
        """
        return self.tsurl + "/callosum/v1" + endpoint

    def get_dependencies_for_all_tables(self):
        """
        Returns a list of dependencies for all tables.
        :return: The dependencies for all tables.
        """
        dt = DependencyTree()
        all_tables = self.get_all_tables()

        for table in all_tables:
            dt.add_table(table=table)

        table_ids = dt.get_table_ids()
        dependencies = self.get_dependents_for_tables(table_ids=table_ids)
        while dependencies.number_tables() > 0:
            dt.extend(other_dependencies=dependencies)
            dependencies = self.get_dependents_for_tables(table_ids=dependencies.get_table_ids())

        return dt

    @api_call
    def get_all_tables(self):
        """
        Returns a list of all tables in the cluster.
        :return: A list of all the tables in the cluster.
        :rtype: list of Table
        """
        tables = []

        # TODO - add the ability to only get certain types of tables.
        # endpoint = self.get_complete_endpoint(
        #    "/metadata/list?type=LOGICAL_TABLE&subtypes=%5BONE_TO_ONE_LOGICAL,AGGR_WORKSHEET%5D")
        endpoint = self.get_complete_endpoint(
            "/metadata/list?type=LOGICAL_TABLE&category=ALL&showhidden=true")

        response = self.session.get(endpoint)
        if response.status_code != 200:
            eprint(f"Unable to retrieve tables: {response.status_code}")
            eprint(f"{response.text}")
            return None

        data = json.loads(response.text)

        for header in data["headers"]:
            t = Table(json_obj=header)
            if not t.isDeleted:  # don't include deleted tables.
                tables.append(t)

        return tables

    @api_call
    def get_dependents_for_tables(self, table_ids):
        """
        Gets dependencies for a list of tables.
        :param table_ids: Table GUID or list of table GUIDs to get dependents for.
        :type table_ids: str | Iterator
        :return: A DependencyTree object that contains all of the dependencies for the table(s).
        :rtype: DependencyTree
        """
        endpoint = self.get_complete_endpoint("/dependency/listdependents?type=LOGICAL_TABLES")
        if isinstance(table_ids, str):  # standardize to a list.
            table_ids = {table_ids}

        # This will be called multiple times, so don't call for the same table more than once.
        tables_to_check = set()
        for table_id in table_ids:
            if table_id not in self._checked_table_ids:
                tables_to_check.add(table_id)
                self._checked_table_ids.add(table_id)

        query_data = {"type": None, "id": "[" + ",".join(tables_to_check) + "]"}
        response = self.session.post(endpoint, data=query_data)
        data = json.loads(response.text)
        # print(json.dumps(data, indent=4, sort_keys=True))

        dt = DependencyTree()
        for table_id in data.keys():
            if len(data[table_id]) > 0:
                dependents = set()
                for object_type in data[table_id].keys():
                    for object_data in data[table_id][object_type]:
                        dependent_id = object_data.get("id", None)
                        dependent_table = dt.get_table(table_guid=dependent_id)
                        if not dependent_table:
                            dependent_table = Table(guid=dependent_id, json_obj=object_data)
                        dt.add_table(table=dependent_table, depends_on=table_id)
                        dependents.add(dependent_id)
                dt.add_table_dependencies(table_id, dependents=dependents)

        return dt
