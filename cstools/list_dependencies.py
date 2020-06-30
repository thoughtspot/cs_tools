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

from cst.api import get_cluster_args, DependencyFinder, DependencyTree
from cst.io import DependencyTreeStdoutWriter, DependencyTreeXLSWriter
from cst.util import eprint


def run_app():
    """
    Main application for finding dependencies.
    :return: Nothing
    """
    args = get_args()

    if valid_args(args):

        df = DependencyFinder(tsurl=args.tsurl, username=args.username,
                              password=args.password, disable_ssl=args.disable_ssl)

        dt = df.get_dependencies_for_all_tables(ignore_ts=args.ignore_ts)
        if args.output_type == "stdout":
            DependencyTreeStdoutWriter().write_dependency_tree(dt=dt)
        elif args.output_type == "excel":
            DependencyTreeXLSWriter.write_to_excel(dt=dt, filename=args.filename)


def get_args():
    """
    Gets the arguments for the application.
    :return: The command arguments.
    :rtype: argparse.Namespace
    """
    parser = get_cluster_args()  # tsurl, username, password, disable_ssl
    parser.add_argument("--output_type", default="stdout", help="Where to write results: stdout, xls, excel.")
    parser.add_argument("--filename", default="stdout", help="Name of the file for Excel files.")
    parser.add_argument("--ignore_ts", action="store_true", default=True, help="Ignore files that start with 'TS:'.")

    return parser.parse_args()


def valid_args(args):
    """
    Validates that the arguments are valid.
    :param args: The arguments provided by the user.
    :type args: argparse.Namespace
    :return: True if valid.
    :rtype: bool
    """
    valid = True
    print(args)

    valid_output_types = ["stdout", "xls", "excel"]

    if not args.tsurl:
        eprint(f"A TS URL must be provided.")
        valid = False

    if not args.output_type in valid_output_types:
        eprint(f'output_type must be one of {",".join(valid_output_types)}')
        valid = False

    if (args.output_type == "xls" or args.output_type == "excel") and not args.filename:
        eprint(f'Excel output requires a filename.')
        valid = False

    # do minimal cleanup.
    if valid:
        # Can't have / at the end of the tsurl.
        if args.tsurl.endswith("/"):
            args.tsurl = args.tsurl[:-1]
        # only return one excel type.
        if args.output_type == "xls":
            args.output_type = "excel"

    return args


if __name__ == "__main__":
    run_app()
