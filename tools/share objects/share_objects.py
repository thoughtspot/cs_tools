"""
Share objects with groups.
"""
from typing import Union, List
import argparse
import logging
import pathlib

from requests.exceptions import SSLError

from thoughtspot_internal.models.metadata import MetadataObject
from thoughtspot_internal.models.security import ObjectType, SharePermission
from thoughtspot_internal.util.ux import FrontendArgumentParser

from _version import __version__


_log = logging.getLogger(__name__)


def _get_group_id (api: 'ThoughtSpot', *, group_name: str) -> Union[str,None]:
    """
    Returns the id for the group with the given name.
    :param group_name: Name of the group to get the ID for.
    :return: The GUID for the group or None if the group name doesn't exist.
    """
    # TODO put the group lists into a data model with easy to user group details.
    group_details = api._metadata.list(type="USER_GROUP")
    for g in group_details.json()["headers"]:
        if group_name == g["name"]:
            return g["id"]
    return None


def _get_table_ids(api: 'ThoughtSpot', *,
                   database_name: str, schema_name: str = "falcon_default_schema", table_name: str = None) -> List[str]:
    """
    Returns a list of table GUIDs.
    """

    table_guids = []
    table_details = api._metadata.list(type="LOGICAL_TABLE", subtype="%5BONE_TO_ONE_LOGICAL%5D")

    for table in table_details.json()["headers"]:
        if "databaseStripe" not in table:  # system tables don't have a databaseStripe.  Don't allow sharing of those.
            continue

        if table_name:  # a specific table was requested
            if database_name == table["databaseStripe"] and schema_name == table["schemaStripe"]:
                # metadata/list returns logical table name not physical so need to make another call
                if table_name == _get_physical_table_name(api, table_id=table['id']):
                    table_guids.append(table["id"])
                    break
        else:
            if database_name == table["databaseStripe"]:
                table_guids.append(table['id'])

    return table_guids if table_guids else None


def _get_physical_table_name(api, *, table_id: str) -> str:
    """
    Returns the physical table name for a given GUID.
    """
    table_details = api._metadata.detail(guid=table_id, type=MetadataObject.LOGICAL_TABLE)
    return table_details.json()["logicalTableContent"]["physicalTableName"]


def _permission_param_to_permission(permission: str) -> SharePermission:
    return {  # should be one of these due to parameter checking
        "view": SharePermission.READ_ONLY,
        "edit": SharePermission.MODIFY,
        "remove": SharePermission.NO_ACCESS
    }[args.permission]


def _share_tables(api, *, group_id, table_ids, permission):
    """
    Shares the tables with the given ID with the group.
    """
    return api._security.share(type=ObjectType.LOGICAL_TABLE, id=table_ids, permission={group_id: permission})


def app(api: 'ThoughtSpot', *, args: argparse.Namespace) -> None:
    """
    This app will share one or more tables from a database with a specified user group.
    """
    try:
        with api:
            group_id = _get_group_id(api=api, group_name=args.group)
            if not group_id:
                msg = f"Group {args.group} wasn't found.  Verify the name and try again."
                _log.error(msg)
            else:
                table_ids = _get_table_ids(api,
                                           database_name=args.database, schema_name=args.schema, table_name=args.table)
                if not table_ids:
                    print(f"No tables found for {args.database}.{args.schema}{f'.{args.table}' if args.table else ''}")
                else:
                    r = _share_tables(api, group_id=group_id, table_ids=table_ids,
                                      permission=_permission_param_to_permission(args.permission))
                    success = "succeeded" if r.status_code == 204 else "failed"
                    print(f'Sharing with group "{args.group}" {success} - Status code: {r.status_code}')
                    if success == "failed":
                        print(r.content)

    except SSLError:
        msg = "SSL certificate verify failed, did you mean to use flag --disable_ssl?"
        _log.error(msg)


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

    parser.add_argument("--group", help="Group to share with.")
    parser.add_argument("--permission", help="Type of permission to assign.", choices=['view','edit','remove'])

    parser.add_argument("--database", help="Database name of tables to share.")
    parser.add_argument("--schema",
                        help="Schema name of tables to share.  Defaults to 'falcon_default_schema'",
                        default="falcon_default_schema")
    parser.add_argument("--table",
                        help="Name of table to share.  If not provided, all tables in the database will be shared.")

    args = parser.parse_args()

    if args.version:
        parser.print_version(__version__)
        # SystemExit

    errors = []

    if not (args.toml or all(map(bool, [args.username, args.password, args.ts_url]))):
        errors.append(
            'you must provide either tsconfig.toml file OR manually supply all '
            '--username, --password, and --ts_url'
        )

    if not args.database:
        errors.append('you must specify a database name')

    if not args.group:
        errors.append('you must specify a group name')

    if not args.permission:
        errors.append('you must specify a permission for sharing')

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
    app(api=ts_api, args=args)
