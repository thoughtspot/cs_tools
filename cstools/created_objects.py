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
import pathlib
import csv

from cst.api import get_cluster_args, Metadata
from cst.util import eprint


def run_app():
    """
    Main application for generating a CSV of created objects.
    :return: Nothing
    """
    parser = get_parser()
    args = parser.parse_args()

    if not valid_args(args):
        parser.print_help()
        return

    auth = {
        'tsurl': args.tsurl,
        'username': args.username,
        'password': args.password,
        'disable_ssl': args.disable_ssl
    }

    meta = Metadata(**auth)
    data = [
        *[{**e, **{'type': 'answer'}} for e in meta.get_list('QUESTION_ANSWER_BOOK')],
        *[{**e, **{'type': 'pinboard'}} for e in meta.get_list('PINBOARD_ANSWER_BOOK')]
    ]

    with pathlib.Path(args.filename).open('w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            'object_id', 'type', 'author_display_name', 'created', 'modified'
        ])

        for row in data:
            writer.writerow([
                row['id'],
                row['type'],
                row['authorDisplayName'],
                row['created'],
                row['modified']
            ])


def get_parser():
    """
    Gets the arguments for the application.

    :return: The command arguments.
    :rtype: argparse.ArgumentParser
    """
    parser = get_cluster_args()  # tsurl, username, password, disable_ssl
    parser.add_argument("--filename", help="Name of the CSV file.")
    return parser


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

    if not args.tsurl:
        eprint(f"A TS URL must be provided.")
        valid = False

    p = pathlib.Path(args.filename)

    if p.exists():
        eprint(f'{p.as_posix()} already exists!')
        valid = False

    if p.suffix != '.csv':
        eprint(f'must specify a CSV format, got "{p.as_posix()}"')
        valid = False

    # do minimal cleanup.
    if valid:
        # Can't have / at the end of the tsurl.
        if args.tsurl.endswith("/"):
            args.tsurl = args.tsurl[:-1]

    return valid


if __name__ == "__main__":
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    run_app()
