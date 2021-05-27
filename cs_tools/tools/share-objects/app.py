from typing import Optional, List
import logging
import enum

from typer import Argument as A_, Option as O_
import typer

from cs_tools.helpers.cli_ux import console, show_tool_options, frontend
from cs_tools.settings import TSConfig
from cs_tools.api import ThoughtSpot
from cs_tools.models.security import SharePermission


log = logging.getLogger(__name__)


class PermissionType(str, enum.Enum):
    VIEW = 'view'
    EDIT = 'edit'
    REMOVE = 'remove'


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


def _permission_param_to_permission(permission: str) -> SharePermission:
    """
    """
    # should be one of these due to parameter checking
    _mapping = {
        'view': SharePermission.READ_ONLY,
        'edit': SharePermission.MODIFY,
        'remove': SharePermission.NO_ACCESS
    }
    return _mapping[permission]


app = typer.Typer(
    help="""
    Share one or more tables from a database with a specified user group.
    """,
    callback=show_tool_options,
    invoke_without_command=True
)


@app.command()
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

    with ThoughtSpot(cfg) as api:
        group_id = _get_group_id(api, group_name=group)

        if not group_id:
            console.print(
                f'[red]Group "{group}" not found. Verify the name and try again.[/]'
            )
            raise typer.Exit()

        table_ids = _get_table_ids(api, db=database, schema=schema, table=table)

        if not table_ids:
            console.print(f"No tables found for {database}.{schema}{f'.{table}' if table else ''}")
            raise typer.Exit()

        r = api._security.share(
                type='LOGICAL_TABLE',
                id=table_ids,
                permission={group_id: _permission_param_to_permission(permission)}
            )

        status = '[green]success[/]' if r.status_code == 204 else '[red]failed[/]'
        console.print(f'Sharing with group "{group}": {status}')

        if r.status_code != 204:
            log.error(r.content)
