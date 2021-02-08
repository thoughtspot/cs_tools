from typing import List, Dict, Any
import datetime as dt
import argparse
import logging
import pathlib
import csv

from thoughtspot.const import FMT_TSLOAD_DATETIME
from thoughtspot_internal.util.datetime import to_datetime
from thoughtspot_internal.util.ux import FrontendArgumentParser

from _version import __version__


_log = logging.getLogger(__name__)


def _user_groups_info(api):
    """
    """
    r = api.user.list()
    groups = []
    users = []

    for principal in r.json():
        if 'GROUP' in principal['principalTypeEnum']:
            groups.append({
                'name': principal['name'],
                'display_name': principal['displayName'],
                'description': principal.get('description', ''),
                'created': to_datetime(principal['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                'modified': to_datetime(principal['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME)
            })

        if 'USER' in principal['principalTypeEnum']:
            for group in principal['groupNames']:
                users.append({
                    'name': principal['name'],
                    'display_name': principal['displayName'],
                    'email': principal['mail'],
                    'group': group,
                    'created': to_datetime(principal['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                    'modified': to_datetime(principal['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME)
                })

    return users, groups


def app(api: 'ThoughtSpot', dirname: pathlib.Path) -> None:
    """
    Main application logic.

    """
    file_opts = {'mode': 'w', 'encoding': 'utf-8', 'newline': ''}

    with api:
        users, groups = _user_groups_info(api)

        with open(dirname / 'users.csv', **file_opts) as c:
            seen = []
            u = []

            for user in users:
                if user['name'] not in seen:
                    seen.append(user['name'])
                    u.append({k: v for k, v in user.items() if k != 'group'})

            writer = csv.DictWriter(c, u[0].keys())
            writer.writeheader()
            writer.writerows(u)

        with open(dirname / 'groups.csv', **file_opts) as c:
            writer = csv.DictWriter(c, groups[0].keys())
            writer.writeheader()
            writer.writerows(groups)

        with open(dirname / 'users_groups.csv', **file_opts) as c:
            asso = [{'user_name': u['name'], 'group_name': u['group']} for u in users]
            writer = csv.DictWriter(c, asso[0].keys())
            writer.writeheader()
            writer.writerows(asso)


def parse_arguments() -> argparse.Namespace:
    """
    CLI interface to this script.
    """
    parser = FrontendArgumentParser(
                 prog=pathlib.Path(__file__).name,
                 description=__doc__,
                 epilog='Additional help can be found at https://github.com/thoughtspot/cs_tools',
             )

    parser.add_argument('--dirname', action='store', help='output directory to save usergroup data')
    args = parser.parse_args()

    if args.version:
        parser.print_version(__version__)
        # SystemExit

    errors = []

    if not args.dirname:
        errors.append('--dirname is a required argument that is missing')

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
    app(ts_api, dirname=pathlib.Path(args.dirname))
