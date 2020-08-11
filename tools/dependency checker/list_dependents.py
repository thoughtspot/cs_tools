from typing import List, Dict, Any
import argparse
import logging
import csv

from requests.exceptions import SSLError

from thoughtspot.util.datetime import timestamp_to_datetime
from thoughtspot.util.swagger import to_array
from thoughtspot.util.ux import eprint
from thoughtspot.const import FMT_TSLOAD_DATETIME


_log = logging.getLogger(__name__)
FLAT_API_RESPONSE = List[Dict[str, Any]]


def _internal_name_lookup(name: str) -> str:
    """
    Maps an object type to a business friendly name.
    """
    mapping = {
        'QUESTION_ANSWER_BOOK': 'saved answer',
        'PINBOARD_ANSWER_BOOK': 'pinboard',
        'USER_DEFINED': 'imported table',
        'ONE_TO_ONE_LOGICAL': 'table',
        'AGGR_WORKSHEET': 'view',

        # what's the difference here...?
        'LOGICAL_TABLE': 'worksheet',
        'WORKSHEET': 'worksheet',

        # so far unsused from Tyler's script
        'INSIGHT': 'spotiq insight',
        'PINBOARD': 'pinboard',
    }

    return mapping[name]


def _url_lookup(name: str) -> str:
    """
    Maps a business friendly name to its URL part.
    """
    mapping = {
        'imported table': 'data/tables',
        'worksheet': 'data/tables',
        'table': 'data/tables',
        'view': 'data/tables',
        'spotiq insight': 'insight'
    }

    try:
        return mapping[name]
    except KeyError:
        return name.replace(' ', '-')


def _get_worksheets(api) -> FLAT_API_RESPONSE:
    """
    Get data for all the client's worksheets in a cluster.

    Data returned each worksheet:
        - name
        - type
        - guid
    """
    r = api._metadata.list(type='LOGICAL_TABLE', category='ALL', showHidden=True)
    worksheets = []

    for item in r.json()['headers']:
        if item['type'] == 'CALENDAR_TABLE' or item['name'].startswith('TS:'):
            continue

        worksheets.append({
            'name': item['name'],
            'type': item['type'],
            'guid': item['id']
        })

    return worksheets


def _get_dependents(api) -> FLAT_API_RESPONSE:
    """
    Return a flat data structure of dependents.

    Data returned about each dependent:
        - parent_guid
        - parent_type
        - parent_name
        - parent_url
        - guid
        - type
        - name
        - url
        - author_name
        - author_display_name
        - created_at   [note: str in TS_DATETIME_FMT]
        - modified_at  [note: str in TS_DATETIME_FMT]
    """
    TS_HOST = api.config.thoughtspot.host

    worksheets = _get_worksheets(api)
    guids = map(lambda e: e['guid'], worksheets)

    r = api._dependency.list_dependents(type=None, id=to_array(guids))
    dependencies = []

    for parent_guid, info in r.json().items():
        try:
            parent = next((w for w in worksheets if w['guid'] == parent_guid))
        except StopIteration:
            _log.error(
                '>>>>> ERROR <<<<<<',
                f'\n{parent_guid}',
                f'\n{info}'
            )
            return []
        else:
            parent_type = _internal_name_lookup(parent['type'])
            parent_url = f"{TS_HOST}/#/{_url_lookup(parent_type)}/{parent['guid']}"

        # NOTE:
        #
        # this dep tree will only go 1 level deep, we might be able to sort
        # the list_dependents api response [note: r.json().items()] to allow
        # us to print the entire dependency tree linearly.
        _dependency_tree_msg = (
            f"\n{parent['name']}  <-- ({parent['type']} aka '{parent_type}')"
            f'\n  has the following dependents..'
        )

        for dependency_type, dependents in info.items():
            dependent_type = _internal_name_lookup(dependency_type)

            for dependent in dependents:
                # TODO: subclassify insights? (a type of pinboard, SpotIQ)
                #
                # if dependent_type == 'pinboard':
                #     [snipped from tyler's old scripts]
                #     if dependent['reportContent']['sheets'][0]['sheetContent']['sheetContentType'] == 'INSIGHT' ?
                #     print(dependent)
                #

                url = f"{TS_HOST}/#/{_url_lookup(dependent_type)}/{dependent['id']}"
                created = timestamp_to_datetime(dependent['created'], unit='ms')
                modified = timestamp_to_datetime(dependent['modified'], unit='ms')

                _dependency_tree_msg += (
                    f"\n  - {dependent['name']}  <-- ({dependency_type} aka "
                    f"{dependent_type})"
                )

                dependencies.append({
                    'parent_guid': parent['guid'],
                    'parent_type': parent_type,
                    'parent_name': parent['name'],
                    'parent_url': parent_url,
                    'guid': dependent['id'],
                    'type': dependent_type,
                    'name': dependent['name'],
                    'url': url,
                    'author_name': dependent['authorName'],
                    'author_display_name': dependent['authorDisplayName'],
                    'created_at': created.strftime(FMT_TSLOAD_DATETIME),
                    'modified_at': modified.strftime(FMT_TSLOAD_DATETIME)
                })\

        _log.debug(f'dependency tree:\n{_dependency_tree_msg}\n')

    return dependencies


def app(api: 'ThoughtSpot', *, filename: str) -> None:
    """
    Main application logic.

    This app will grab all the worksheet/view/table dependents from the
    API and then save that data at <filename> in CSV format. This data
    can be manually observed with a tool like Microsoft Excel, or
    reimported back into ThoughtSpot and joined to the TS BI: Sever
    table on the parent_guid.
    """
    try:
        with api:
            dependencies = _get_dependents(api)
    except SSLError:
        _log.error(
            'SSL certificate verify failed, did you mean to use flag --disable_ssl?'
        )
        return

    with open(filename, mode='w', encoding='utf-8', newline='') as c:
        writer = csv.DictWriter(c, dependencies[0].keys())
        writer.writeheader()
        writer.writerows(dependencies)


def parse_arguments():
    """
    CLI interface to this script.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--filename', required=True, action='store', help='location of the CSV file to output dependents')
    parser.add_argument('--toml', help='location of the tsconfig.toml configuration file')
    parser.add_argument('--ts_url', help='the url to thoughtspot, https://my.thoughtspot.com')
    parser.add_argument('--username', help='frontend user to authenticate to ThoughtSpot with')
    parser.add_argument('--password', help='frontend password to authenticate to ThoughtSpot with')
    parser.add_argument('--disable_ssl', action='store_true', help='whether or not to ignore SSL errors')
    parser.add_argument('--log_level', default='INFO', metavar='INFO', help='verbosity of the logger (used for debugging)')

    try:
        args = parser.parse_args()
        parse_failed = False
    except Exception:
        parser.print_usage()
        raise SystemExit()

    if not (args.toml or all(map(bool, [args.username, args.password, args.ts_url]))):
        msg = (
            '\n[ERROR] you must provide either tsconfig.toml file OR manually supply '
            'all --username, --password, and --ts_url\n'
        )
        eprint(msg)  # TODO: logging
        parse_failed = True

    if parse_failed:
        parser.print_help()
        raise SystemExit()

    return args


if __name__ == '__main__':
    from thoughtspot.settings import TSConfig
    from thoughtspot.api import ThoughtSpot

    args = parse_arguments()

    if args.toml:
        config = TSConfig.from_toml(args.toml)
    else:
        data = {
            'thoughtspot': {
                'host': args.ts_url,
                'disable_ssl': args.disable_ssl
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
    app(ts_api, filename='./test.csv')
