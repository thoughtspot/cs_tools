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

# Contains utility functions used by other parts of the system.

import argparse
import sys


def eprint(*args, **kwargs):
    """
    Prints to standard error similar to regular print.
    :param args:  Positional arguments.
    :param kwargs:  Keyword arguments.
    """
    print(*args, file=sys.stderr, **kwargs)


def printif(condition, text):
    """
    Prints out the text if the condition is met.  Simplify tracing.
    :param condition: The condition to check.
    :param condition: bool
    :param text: The text to print.
    :param test: str
    :return: Nothing.
    """
    if condition:
        print(text)


class BaseAPIArgParser:
    """
    Base argument parser to be used in different apps.  Call get_parser to get the base parser and validate to do
    validation.
    """
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("-t", "--thoughtspot_host", required=True,
                                 help="URL or IP, e.g. https:thoughtspot.mycompany.com or https://1.1.1.1")
        self.parser.add_argument("-u", "--username", default="tsadmin", required=True,
                                 help="username - must have administrative privileges")
        self.parser.add_argument("-p", "--password", default="admin", required=True,
                                 help="password - must have administrative privileges")

    def get_parser(self) -> argparse.ArgumentParser:
        """
        Returns the base arg parser.
        :return: The base arg parser.  Note that this returns the original, which can be updated.
        :rtype: argparse.ArgumentParser
        """
        return self.parser

    def valid_args(self) -> bool:
        """
        Validates the base arguments.
        :return: True if the base arguments are valid.
        :rtype: bool
        """
        errors = []
        dict_args = vars(self.parser)
        for k in dict_args.keys():
            if not dict_args[k]:
                errors.append(f"Missing or empty argument {k}")

        valid = not errors
        if not valid:
            eprint(errors)

        return valid

