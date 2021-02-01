from typing import List, Dict, Any
import datetime as dt
import argparse
import logging
import pathlib
import csv

from requests.exceptions import SSLError

from thoughtspot_internal.util.ux import FrontendArgumentParser

from _version import __version__


_log = logging.getLogger(__name__)


def _user_groups_info():
    pass


def app(api: 'ThoughtSpot', filename: pathlib.Path) -> None:
    """
    Main application logic.

    """
    with api:
        data = _user_groups_info(api)

        with open(filename, mode='w', encoding='utf-8', newline='') as c:
            writer = csv.DictWriter(c, data[0].keys())
            writer.writeheader()
            writer.writerows(data)


def parse_arguments() -> argparse.Namespace:
    """
    CLI interface to this script.
    """
    parser = FrontendArgumentParser(
                 prog=pathlib.Path(__file__).name,
                 description=__doc__,
                 epilog='Additional help can be found at https://github.com/thoughtspot/cs_tools',
             )

    parser.add_argument('--filename', action='store', help='output file to save user data')
    args = parser.parse_args()

    if args.version:
        parser.print_version(__version__)
        # SystemExit

    errors = []

    if not args.filename:
        errors.append('--filename is a required argument that is missing')

    if not (args.toml or all(map(bool, [args.username, args.password, args.ts_url]))):
        errors.append(
            'you must provide either tsconfig.toml file OR manually supply all '
            '--username, --password, and --ts_url'
        )

    if errors:
        parser.errored(errors)
        # SystemExit

    return args


if __name__ == '__main__':
    from thoughtspot.settings import TSConfig
    from thoughtspot_internal.api import ThoughtSpot

    args = parse_arguments()

    if args.toml:
        config = TSConfig.from_toml(args.toml)
    else:
        data = {
            'thoughtspot': {
                'host': args.ts_url,
                'disable_ssl': args.disable_ssl,
                'disable_sso': args.disable_sso
            },
            'auth': {
                'frontend': {
                    'username': args.username,
                    'password': args.password
                }
            },
            'logging': {
                'level': args.log_level
            }
        }
        config = TSConfig(**data)

    ts_api = ThoughtSpot(config)
    app(ts_api, filename=pathlib.Path(args.filename))
