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


def _format_table_info_data(data: List[dict]) -> List[dict]:
    """
    TODO
    """
    data = [
        {
            'database_name': e.get('database'),
            'schema_name': e.get('schema'),
            'table_name': e.get('name'),
            'table_guid': e['guid'],
            'state': e.get('state'),
            'database_version': e.get('databaseVersion'),
            'serving_version': e.get('servingVersion'),
            'building_version': e.get('buildingVersion'),
            'build_duration': e.get('buildDuration'),
            'last_build_time': e.get('lastBuildTime'),
            'is_known': e.get('isKnown'),
            'database_status': e.get('databaseStatus'),
            'last_uploaded_at': dt.datetime.fromtimestamp(e.get('lastUploadedAt', 0) / 1_000_000).replace(microsecond=0).isoformat(),
            # 'last_uploaded_at': pd.to_datetime(e.get('lastUploadedAt'], unit='ms').isoformat(),
            'num_of_rows': e.get('numOfRows'),
            'approx_bytes_size': e.get('approxByteSize'),
            'uncompressed_bytes_size': e.get('uncompressedByteSize'),
            'row_skew': e.get('rowSkew'),
            'num_shards': e.get('numShards'),
            'csv_size_with_replication_mb': e.get('csvSizeWithReplicationMB'),
            'replicated': e.get('replicated'),
            'ip': 'all' if str(e['ip']) == '-1' else e['ip']
        }
        for e in data['tables']
    ]
    return data


def _to_csv(data: List[Dict[str, Any]], fp: pathlib.Path):
    """
    TODO
    """
    with fp.open(mode='w', encoding='utf-8', newline='') as c:
        writer = csv.DictWriter(c, data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def app(api: 'ThoughtSpot', directory: pathlib.Path) -> None:
    """
    Main application logic.

    """
    try:
        with api:
            data = _format_table_info_data(api._periscope.sage_combinedtableinfo().json())
            _to_csv(data, fp=directory / 'table_info.csv')
    except SSLError:
        msg = 'SSL certificate verify failed, did you mean to use flag --disable_ssl?'
        _log.error(msg)
        return


def parse_arguments() -> argparse.Namespace:
    """
    CLI interface to this script.
    """
    parser = FrontendArgumentParser(
                 prog=pathlib.Path(__file__).name,
                 description=__doc__,
                 epilog='Additional help can be found at https://github.com/thoughtspot/cs_tools',
             )

    parser.add_argument('--directory', action='store', help='directory of where to save CSV output')
    args = parser.parse_args()

    if args.version:
        parser.print_version(__version__)
        # SystemExit

    errors = []

    if not args.directory:
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
    app(ts_api, directory=pathlib.Path(args.directory))
