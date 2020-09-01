"""
Find all objects in your ThoughtSpot platform of a specified type, and
return their dependents.
"""
from typing import List, Dict, Any
import argparse
import logging
import pathlib
import csv

from requests.exceptions import SSLError
from thoughtspot.const import FMT_TSLOAD_DATETIME

from cs_tools.models.metadata import MetadataObject
from cs_tools.util.datetime import to_datetime
from cs_tools.util.swagger import to_array
from cs_tools.util.ux import FrontendArgumentParser

from _version import __version__


_log = logging.getLogger(__name__)
FLAT_API_RESPONSE = List[Dict[str, Any]]


def _to_friendly_name(metadata_type: str) -> str:
    """
    Translate internal names to something more end-user friendly.

    TODO: finalize and move to util.ux
    """
    mapping = {
        'QUESTION_ANSWER_BOOK': 'saved answer',
        'PINBOARD_ANSWER_BOOK': 'pinboard',
        'LOGICAL_TABLE': 'worksheet',
        'USER_DEFINED': 'imported table',
        'ONE_TO_ONE_LOGICAL': 'table',
        'AGGR_WORKSHEET': 'view',
        'INSIGHT': 'spotiq insight'
    }

    return mapping.get(metadata_type, metadata_type)


def _to_url(host: str, metadata: FLAT_API_RESPONSE) -> str:
    """
    Build a frontend URL for a given metadata object.

    TODO: finalize and move to util.ux
    """
    mapping = {
        'QUESTION_ANSWER_BOOK': 'saved-answer',
        'PINBOARD_ANSWER_BOOK': 'pinboard',
        'LOGICAL_TABLE': 'data/tables',
        'USER_DEFINED': 'data/tables',
        'ONE_TO_ONE_LOGICAL': 'data/tables',
        'AGGR_WORKSHEET': 'data/tables',
        'INSIGHT': 'insight'
    }

    try:
        guid  = metadata['guid']
    except KeyError:
        _log.warning(f'metadata does not have a known guid:\n{metadata}')
        return 'n/a'

    type_ = metadata['type']

    try:
        page = mapping[type_]
    except KeyError:
        return 'n/a'

    return f'{host}/#/{page}/{guid}'


def _get_metadata(api: 'ThoughtSpot', *, metadata_type: str) -> FLAT_API_RESPONSE:
    """
    Return a flat data structure of metadata objects.

    Data returns about each dependent:
        - guid
        - type
        - name
    """
    r = api._metadata.list(type=metadata_type, batchsize=-1, showhidden=True)
    objects = []

    for metadata_object in r.json()['headers']:
        objects.append({
            'guid': metadata_object['id'],
            'type': metadata_type,
            'name': metadata_object['name']
        })

    return objects


def _get_dependents(
    api: 'ThoughtSpot',
    *,
    metadata_type: str='LOGICAL_TABLE'
) -> FLAT_API_RESPONSE:
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
        - created_at
        - modified_at
    """
    parents = _get_metadata(api, metadata_type=metadata_type)
    guids = map(lambda e: e['guid'], parents)
    r = api._dependency.list_dependents(type=metadata_type, id=to_array(guids))

    dependencies = []

    for parent_guid, dependents_info in r.json().items():
        parent = next((p for p in parents if p['guid'] == parent_guid))

        for dependent_type, dependents in dependents_info.items():
            for dependent in dependents:
                dependent['type'] = dependent.get('type', dependent_type)

                dependencies.append({
                    'parent_guid': parent['guid'],
                    'parent_type': _to_friendly_name(parent['type']),
                    'parent_name': parent['name'],
                    'parent_url': _to_url(api.host, parent),
                    'guid': dependent['id'],
                    'type': _to_friendly_name(dependent['type']),
                    'name': dependent['name'],
                    'url': _to_url(api.host, dependent),
                    'author_name': dependent['authorName'],
                    'author_display_name': dependent['authorDisplayName'],
                    'created_at': to_datetime(dependent['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                    'modified_at': to_datetime(dependent['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME)
                })

    return dependencies


def app(api: 'ThoughtSpot', *, filename: str, metadata_type: str) -> None:
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
            dependencies = _get_dependents(api, metadata_type=metadata_type)
    except SSLError:
        msg = 'SSL certificate verify failed, did you mean to use flag --disable_ssl?'
        _log.error(msg)
        return

    with open(filename, mode='w', encoding='utf-8', newline='') as c:
        writer = csv.DictWriter(c, dependencies[0].keys())
        writer.writeheader()
        writer.writerows(dependencies)


def parse_arguments() -> argparse.Namespace:
    """
    CLI interface to this script.
    """
    METADATA_TYPES = list(map(lambda e: e.value, list(MetadataObject)))

    parser = FrontendArgumentParser(
                 prog=pathlib.Path(__file__).name,
                 description=__doc__,
                 epilog='Additional help can be found at https://github.com/thoughtspot/cs_tools',
             )

    parser.add_argument('--filename', action='store', help='location of the CSV file to output dependents')

    # TODO:
    #   make this more user-friendly. We want the user to specify a type that's easy
    #   for them to understand.
    #
    #   GOOD: worksheet, table, answer
    #    BAD: LOGICAL_WORKSHEET, ONE_TO_ONE_LOGICAL, QUESTION_ANSWER_BOOK
    #
    #   extra credit: how could we achieve "spot iq insight"
    #   extra credit: how could we achieve "system table" vs "user defined table" vs "table"
    #
    parser.add_argument(
        '--object_type', default='LOGICAL_TABLE', action='store', choices=METADATA_TYPES,
        help='type of object to find dependents from'
    )

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
    from cs_tools.api import ThoughtSpot

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
    app(ts_api, filename=args.filename, metadata_type=args.object_type)
