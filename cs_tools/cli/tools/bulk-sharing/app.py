import logging

from thoughtspot_tml import _yaml
import uvicorn
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.ux import rich_console
from cs_tools.cli.ux import CSToolsArgument as Arg
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import CSToolsApp
from cs_tools.types import GUID, ShareModeAccessLevel

from .web_app import _scoped
from . import work

log = logging.getLogger(__name__)
app = CSToolsApp(
    help="""
    Scalably manage your table- and column-level security right in the browser.

    Setting up Column Level Security (especially on larger tables) can be time-consuming
    when done directly in the ThoughtSpot user interface. The web interface provided by
    this tool will allow you to quickly understand the current security settings for a
    given table across all columns, and as many groups as are in your platform. You may
    then set the appropriate security settings for those group-table combinations.
    """,
)


@app.command(dependencies=[thoughtspot])
def cls_ui(ctx: typer.Context, webserver_port: int = Opt(5000, help="port to host the webserver on")):
    """
    Start the built-in webserver which runs the security management interface.
    """
    ts = ctx.obj.thoughtspot
    visit_ip = work._find_my_local_ip()

    _scoped["ts"] = ts

    rich_console.print("starting webserver..." f"\nplease visit [green]http://{visit_ip}:5000/[/] in your browser")

    uvicorn.run(
        "cs_tools.cli.tools.bulk-sharing.web_app:web_app",
        host="0.0.0.0",
        port=webserver_port,
        log_config=None,  # TODO log to file instead of console (less confusing for user)
    )


@app.command(dependencies=[thoughtspot])
def single(
    ctx: typer.Context,
    group: str = Opt(..., help="group to share with"),
    permission: ShareModeAccessLevel = Opt(..., help="permission type to assign"),
    table: str = Opt(None, help='name of the table to share'),
    table_guid: GUID = Opt(None, help='guid of the table to share'),
    connection_guid: GUID = Opt(None, help='guid of the connction to share all tables for'),
):
    """
    Share a Table or Connection with a Group.
    """
    if len([1 for p in (table, table_guid, connection_guid) if p is not None]) != 1:
        rich_console.print(
            "[red]You must provide (only) one of [b blue]table[/] name, [b blue]table-guid[/], or "
            "[b blue]connection-guid[/]"
        )
        raise typer.Exit(1)

    ts = ctx.obj.thoughtspot
    group_id = ts.group.guid_for(group_name=group)

    if not group_id:
        rich_console.log(
            f'[red]Group "{group}" not found. Verify the name and try again.[/]'
        )
        raise typer.Exit()

    if table:
        r = ts.api.metadata_list(metadata_type="LOGICAL_TABLE", pattern=table)
        data = r.json()

        if not data["headers"]:
            rich_console.log(f"[b red]no [b blue]table[/] found with name '[b green]{table}[/]'")
            raise typer.Exit(1)

        elif len(data["headers"]) > 1:
            rich_console.log(
                f"[b red]more than 1 [b blue]table[/] found with name [b blue]{table}[/], try using the "
                f"[b blue]--table-guid[/] instead"
            )

            for table in data["headers"]:
                rich_console.log(f"{table['id']} [b blue]{table['name']}")

            raise typer.Exit(1)

        table_ids = [t["id"] for t in data["headers"]]

    if table_guid:
        table_ids = [table_guid]

    if connection_guid:
        cnxn_data = _yaml.load(ts.api.connection_export(guid=connection_guid).text)
        table_ids = [table["id"] for table in cnxn_data["table"]]

    if not table_ids:
        rich_console.log("No tables found..")
        raise typer.Exit()

    r = ts.api.security_share(metadata_type='LOGICAL_TABLE', guids=table_ids, permissions={group_id: str(permission)})
    status = "[b green]Success" if r.is_success else "[b red]Failed[/]"
    rich_console.log(f"Sharing with group [b blue]{group}[/]: {status}")

    if r.status_code != 204:
        log.error(r.content)
