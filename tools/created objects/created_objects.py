from typing import Union, Dict, List, Any
import argparse
import logging
import pathlib
import csv

from requests.exceptions import SSLError

from thoughtspot.models.metadata import MetadataObject
from thoughtspot.util.datetime import to_datetime
from thoughtspot.util.ux import FrontendArgumentParser
from thoughtspot.const import FMT_TSLOAD_DATETIME

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


def _get_metadata(
    api: 'ThoughtSpot',
    *,
    metadata_type: Union[str, List[str]]=None
) -> FLAT_API_RESPONSE:
    """
    Return a flat data structure of metadata objects.

    Data returns about each object:
        - guid
        - type
        - name
        - author_name
        - author_display_name
        - created_at
        - modified_at
    """
    if metadata_type is None:
        metadata_types = ...
    elif isinstance(metadata_type, str):
        metadata_types = [metadata_type]

    metadata = []

    for metadata_type in metadata_types:
        r = api._metadata.list(type=metadata_type, batchsize=-1, showhidden=False)
        data = r.json().get('headers', [])

        for point in data:
            metadata.append({
                'guid': point['id'],
                'type': _to_friendly_name(point['type']),
                'name': point['name'],
                'author_name': point['authorName'],
                'author_display_name': point['authorDisplayName'],
                'created_at': to_datetime(point['created'], unit='ms').strftime(FMT_TSLOAD_DATETIME),
                'modified_at': to_datetime(point['modified'], unit='ms').strftime(FMT_TSLOAD_DATETIME)
            })

    return metadata


def app(api: 'ThoughtSpot', *, filename: str, metadata_type: str) -> None:
    """
    Main application logic.

    This app will grab all the objects in a platform from the API and
    then save that data at <filename> in CSV format. This data can be
    manually observed with a tool like Microsoft Excel, or reimported
    back into ThoughtSpot and joined to the TS BI: Sever table on the
    guid.
    """
    try:
        with api:
            metadata = _get_metadata(api, metadata_type=metadata_type)
    except SSLError:
        msg = 'SSL certificate verify failed, did you mean to use flag --disable_ssl?'
        _log.error(msg)
        return

    with open(filename, mode='w', encoding='utf-8', newline='') as c:
        writer = csv.DictWriter(c, metadata[0].keys())
        writer.writeheader()
        writer.writerows(metadata)


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
    from thoughtspot.api import ThoughtSpot

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
