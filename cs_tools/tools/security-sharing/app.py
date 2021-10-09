from typing import Optional, List
import logging
import socket
import enum

from typer import Argument as A_, Option as O_  # noqa
import uvicorn
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig
from cs_tools._enums import AccessLevel

from .web_app import _scoped


log = logging.getLogger(__name__)


class PermissionType(str, enum.Enum):
    VIEW = 'view'
    EDIT = 'edit'
    REMOVE = 'remove'


def _find_my_local_ip() -> str:
    """
    Gets the local ip, or loopback address if not found.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(('10.255.255.255', 1))  # does not need to be a valid addr

        try:
            ip = sock.getsockname()[0]
        except IndexError:
            ip = '127.0.0.1'

    return ip


def _get_group_id(api: ThoughtSpot, *, group_name: str) -> Optional[str]:
    """
    Returns the id for the group with the given name.

    Parameters
    ----------
    group_name : str
      name of the group to get the ID for.

    Returns
    -------
    guid : str
      GUID for the group or None if the group name doesn't exist.
    """
    # TODO put the group lists into a data model with easy to user group details.
    group_details = api._metadata.list(type='USER_GROUP')

    for g in group_details.json()['headers']:
        if group_name == g['name']:
            return g['id']

    return None


def _get_table_ids(
    api: ThoughtSpot,
    *,
    db: str,
    schema: str='falcon_default_schema',
    table: str=None
) -> List[str]:
    """
    Returns a list of table GUIDs.
    """
    r = api._metadata.list(type='LOGICAL_TABLE', subtype=['ONE_TO_ONE_LOGICAL'])
    table_details = r.json()['headers']

    guids = []

    for details in table_details:
        # Don't allow sharing of System Tables.
        if 'databaseStripe' not in details:
            continue

        # specific table
        if db == details['databaseStripe'] and schema == details['schemaStripe']:
            if table == _get_physical_table(api, table_id=details['id']):
                guids.append(details['id'])
                break

        # metadata/list returns LOGICA_TABLE name, need another call for physical name
        if table is None:
            if db == details['databaseStripe']:
                guids.append(details['id'])

    return guids or None


def _get_physical_table(api, *, table_id: str) -> str:
    """
    Returns the physical table name for a given GUID.
    """
    r = api._metadata.detail(guid=table_id, type='LOGICAL_TABLE').json()
    return r['logicalTableContent']['physicalTableName']


def _permission_param_to_permission(permission: str) -> AccessLevel:
    """
    """
    # should be one of these due to parameter checking
    _mapping = {
        'view': AccessLevel.read_only,
        'edit': AccessLevel.modify,
        'remove': AccessLevel.no_access
    }
    return _mapping[permission]


app = typer.Typer(
    help="""
    Scalably manage your table- and column-level security right in the browser.

    Setting up Column Level Security (especially on larger tables) can be time-consuming
    when done directly in the ThoughtSpot user interface. The web interface provided by
    this tool will allow you to quickly understand the current security settings for a
    given table across all columns, and as many groups as are in your platform. You may
    then set the appropriate security settings for those group-table combinations.
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def run(
    webserver_port: int=O_(5000, help='port to host the webserver on'),
    **frontend_kw
):
    """
    Start the built-in webserver which runs the security management interface.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)
    visit_ip = _find_my_local_ip()

    with ThoughtSpot(cfg) as ts:
        _scoped['ts'] = ts

        console.print(
            'starting webserver...'
            f'\nplease visit [green]http://{visit_ip}:5000/[/] in your browser'
        )

        uvicorn.run(
            'cs_tools.tools.security-sharing.web_app:web_app',
            host='0.0.0.0',
            port=webserver_port,
            log_config=None   # TODO log to file instead of console (less confusing for user)
        )


@app.command(cls=RichCommand)
@frontend
def share(
    group: str=O_(..., help='group to share with'),
    permission: PermissionType=O_(..., help='permission type to assign'),
    database: str=O_(..., help='name of database of tables to share'),
    schema: str=O_('falcon_default_schema', help='name of schema of tables to share'),
    table: str=O_(None, help='name of the table to share, if not provided then share all tables'),
    **frontend_kw
):
    """
    Share database tables with groups.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as ts:
        group_id = _get_group_id(ts.api, group_name=group)

        if not group_id:
            console.print(
                f'[red]Group "{group}" not found. Verify the name and try again.[/]'
            )
            raise typer.Exit()

        table_ids = _get_table_ids(ts.api, db=database, schema=schema, table=table)

        if not table_ids:
            console.print(f"No tables found for {database}.{schema}{f'.{table}' if table else ''}")
            raise typer.Exit()

        r = ts.api._security.share(
                type='LOGICAL_TABLE',
                id=table_ids,
                permission={group_id: _permission_param_to_permission(permission)}
            )

        status = '[green]success[/]' if r.status_code == 204 else '[red]failed[/]'
        console.print(f'Sharing with group "{group}": {status}')

        if r.status_code != 204:
            log.error(r.content)
