from typing import List, Dict, Any
import logging
import csv

from requests.exceptions import SSLError

from thoughtspot.models.metadata import MetadataObject
from thoughtspot.util.datetime import to_datetime
from thoughtspot.util.swagger import to_array
from thoughtspot.util.ux import FrontendArgumentParser, eprint
from thoughtspot.const import FMT_TSLOAD_DATETIME


_log = logging.getLogger(__name__)
FLAT_API_RESPONSE = List[Dict[str, Any]]


def _get_metadata(api, *, metadata_type) -> FLAT_API_RESPONSE:
    """
    """
    r = api._metadata.list(type=metadata_type, batchsize=-1, showhidden=True)
    objects = []

    for metadata_object in r.json()['headers']:
        objects.append({
            'name': metadata_object['name'],
            'type': metadata_type,
            'guid': metadata_object['id']
        })

    return objects


def _get_dependents(
    api: 'ThoughtSpot',
    *,
    metadata_type='LOGICAL_TABLE'
) -> FLAT_API_RESPONSE:
    """
    Return a flat data structure of dependents.

    Data returned about each dependent:
        - parent_guid
        - parent_type
        - parent_name
        TODO: - parent_url
        - guid
        - type
        - name
        TODO: - url
        - author_name
        - author_display_name
        - created_at
        - modified_at
    """
    objects = _get_metadata(api, metadata_type=metadata_type)
    guids = map(lambda e: e['guid'], objects)
    r = api._dependency.list_dependents(type=metadata_type, id=to_array(guids))

    dependencies = []

    for parent_guid, dependents_info in r.json().items():
        parent = next((m for m in objects if m['guid'] == parent_guid))

        for dependent_type, dependents in dependents_info.items():
            for dependent in dependents:
                dependencies.append({
                    'parent_guid': parent['guid'],
                    'parent_type': parent['type'],
                    'parent_name': parent['name'],
                    # 'parent_url': ...,
                    'guid': dependent['id'],
                    'type': dependent.get('type', dependent_type),
                    'name': dependent['name'],
                    # 'url': ...,
                    'author_name': dependent['authorName'],
                    'author_display_name': dependent['authorDisplayName'],
                    'created_at': to_datetime(dependent['created'], unit='ms'),
                    'modified_at': to_datetime(dependent['modified'], unit='ms')
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
        _log.error(
            'SSL certificate verify failed, did you mean to use flag --disable_ssl?'
        )
        return

    with open(filename, mode='w', encoding='utf-8', newline='') as c:
        # TODO: beautify the end-user output.
        writer = csv.DictWriter(c, dependencies[0].keys())
        writer.writeheader()
        writer.writerows(dependencies)


def parse_arguments():
    """
    CLI interface to this script.
    """
    OBJECT_TYPES = list(map(lambda e: e.value, list(MetadataObject)))

    parser = FrontendArgumentParser()
    parser.add_argument('--filename', required=True, action='store', help='location of the CSV file to output dependents')
    parser.add_argument('--object_type', required=True, action='store', choices=OBJECT_TYPES, help='type of object to find dependents from')

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
