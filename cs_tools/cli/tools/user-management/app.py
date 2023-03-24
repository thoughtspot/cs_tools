from typing import List
import itertools as it
import logging
import json

import typer
import httpx

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.api._utils import SYSTEM_USERS
from cs_tools.cli.layout import LiveTasks
from cs_tools.cli.types import MetadataType, MultipleChoiceType, SyncerProtocolType
from cs_tools.cli.ux import rich_console
from cs_tools.cli.ux import CSToolsArgument as Arg
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import CSToolsApp
from cs_tools.cli.dependencies.syncer import DSyncer

from . import _extended_rest_api_v1
from . import layout
from . import work

log = logging.getLogger(__name__)
app = CSToolsApp(help="""Manage Users and Groups in bulk.""")


@app.command(dependencies=[thoughtspot])
def transfer(
    ctx: typer.Context,
    from_username: str = Opt(..., "--from", help="username of the current content owner"),
    to_username: str = Opt(..., "--to", help="username to transfer content to"),
    tags: str = Opt(
        None,
        custom_type=MultipleChoiceType(),
        help="if specified, only move content marked with one or more of these tags",
    ),
    metadata_types: List[MetadataType] = Opt(
        None,
        custom_type=MetadataType(to_system_types=True, include_subtype=True),
        help="if specified, only move specific types of objects",
    ),
    guids: str = Opt(
        None,
        custom_type=MultipleChoiceType(),
        help="if specified, only move specific objects",
    ),
    include_dataflow: bool = Opt(False, "--include-dataflow", help="whether or not to include DataFlow jobs"),
):
    """
    Transfer ownership of objects from one User to another.

    Tags, Metadata Types, and GUIDs constraints are applied in OR fashion.
    """
    ts = ctx.obj.thoughtspot

    tasks = [
        ("gather_content", f"Getting content for [b blue]{from_username}[/]"),
        ("transfer_ownership", f"Setting [b blue]{to_username}[/] as the content Author"),
    ]

    if ts.platform.deployment == "software":
        tasks.append(("transfer_dataflow", f"Transferring DataFlow ownership to [b blue]{to_username}[/]"))

    with LiveTasks(tasks, console=rich_console) as tasks:
        guids_to_transfer = set()

        with tasks["gather_content"]:
            if (tags or guids or metadata_types):
                include = None if not metadata_types else [t[0] for t in metadata_types]
                subtype = None if not metadata_types else [t[1] for t in metadata_types if t[1] is not None]
                content = ts.metadata.find(author=from_username, include_types=include, include_subtypes=subtype)

                for header in content:
                    if tags and set(tags).intersection(tag["name"] for tag in header["tags"]):
                        guids_to_transfer.add(header["id"])

                    if header["metadata_type"] in (include or []) and header["type"] in (*(subtype or []), None):
                        guids_to_transfer.add(header["id"])

                    if guids and header["id"] in guids:
                        guids_to_transfer.add(header["id"])

        with tasks["transfer_ownership"]:
            extra = {}

            if (tags or guids or metadata_types):
                if not guids_to_transfer:
                    rich_console.log(
                        f"No content found for [b blue]{from_username}[/] with [b blue]--tags[/] or "
                        f"[b blue]--guids[/]"
                    )
                    raise typer.Exit(1)

                extra["object_guids"] = list(guids_to_transfer)

            try:
                ts.api.user_transfer_ownership(from_username=from_username, to_username=to_username, **extra)
            except httpx.HTTPStatusError as e:
                log.debug(e, exc_info=True)
                raise typer.Exit(1)

            rich_console.log(
                f"Transferred {len(guids_to_transfer) or 'all'} objects from [b blue]{from_username}[/] to "
                f"[b blue]{to_username}[/]"
            )

        if ts.platform.deployment == "software":
            with tasks["transfer_dataflow"]:
                _extended_rest_api_v1.dataflow_transfer_ownership(
                    ts.api,
                    from_username=from_username,
                    to_username=to_username
                )


@app.command(dependencies=[thoughtspot])
def rename(
    ctx: typer.Context,
    from_username: str = Opt(None, "--from", help="current username"),
    to_username: str = Opt(None, "--to", help="new username"),
    syncer: DSyncer = Opt(
        None,
        custom_type=SyncerProtocolType(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options"
    ),
    remapping: str = Opt(None, help="directive to find usernames to sync at", rich_help_panel="Syncer Options"),
):
    """
    Rename Users from one username to another.

    If you are renaming from an external data source, your data must follow the
    tabular format below.

    \b
        +----------------+---------------------------+
        | from_username  |        to_username        |
        +----------------+---------------------------+
        | cs_tools       | cstools                   |
        | namey.namerson | namey@thoughtspot.com     |
        | fake.user      | fake.user@thoughtspot.com |
        +----------------+---------------------------+
    """
    if None in (from_username, to_username):
        rich_console.print(
            f"You must supply both [b blue]--from[/], and [b blue]--to[/], "
            f"got [b blue]--from '{from_username}' --to '{to_username}'"
        )
        raise typer.Exit(-1)

    ts = ctx.obj.thoughtspot
    users_map = {}

    if syncer is None:
        users_map[from_username] = to_username
    
    elif remapping is None:
        rich_console.print("[red]you must provide a syncer directive to --remapping")
        raise typer.Exit(-1)

    else:
        for row in syncer.load(remapping):
            users_map[row["from_username"]] = row["to_username"]
    
    tasks = [
        ("gather_users", f"Getting information on {len(users_map)} existing Users in ThoughtSpot"),
        ("update_users", f"Attempting update for {len(users_map)} Users"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:
        failed = []

        with tasks["gather_users"]:
            responses = []

            for from_username in users_map:
                if from_username in SYSTEM_USERS:
                    log.info(f"[b yellow]renaming [b blue]{from_username}[/] is [b red]not allowed")
                    continue

                try:
                    r = ts.api.user_read(name=from_username)
                except httpx.HTTPStatusError as e:
                    log.error(f"failed to find user [b blue]{from_username}[/]")
                    r = e.response

                responses.append(r)

        with tasks["update_users"]:
            for from_username, to_username, r in zip(users_map.items(), responses):
                if r.is_error or from_username in SYSTEM_USERS:
                    continue

                user_info = r.json()
                user_info["header"]["name"] = to_username

                try:
                    ts.api.user_update(user_guid=user_info["header"]["id"], content=user_info)
                except httpx.HTTPStatusError:
                    header = user_info["header"]
                    user = f"{header['id']} [b blue]{header['displayName']}[/] ({from_username})"
                    log.error(f"failed to update user {user}", exc_info=True)
                    failed.append(from_username)

    if failed:
        log.warning(
            f"[b yellow]Failed to update {len(failed)} Users"
            f"\n - "
            f"\n - ".join(failed)
        )


@app.command(dependencies=[thoughtspot])
def sync(
    ctx: typer.Context,
    apply_changes: bool = Opt(
        False,
        "--apply-changes / --dry-run",
        help="test your sync to ThoughtSpot",
    ),
    new_user_password: str = Opt(None, help="password to set for all newly created users"),
    remove_deleted: bool = Opt(
        False,
        "--remove-deleted",
        help="delete users and groups not found after loading from the syncer"
    ),
    syncer: DSyncer = Opt(
        ...,
        custom_type=SyncerProtocolType(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options"
    ),
    users: str = Opt(
        "ts_auth_sync_users",
        help="directive to find users to sync at",
        rich_help_panel="Syncer Options"
    ),
    groups: str = Opt(
        "ts_auth_sync_groups",
        help="directive to find groups to sync at",
        rich_help_panel="Syncer Options"
    ),
    associations: str = Opt(
        "ts_auth_sync_xref",
        help="directive to find associations to sync at",
        rich_help_panel="Syncer Options"
    ),
    export: bool = Opt(
        False,
        "--export",
        help="if specified, dump principals to the syncer instead of loading into ThoughtSpot",
    ),
    create_empty: bool = Opt(
        False,
        "--create-empty",
        help="write the structure of principal data to your syncer without any data",
        rich_help_panel="Syncer Options"
    ),
):
    """
    Sync your Users and Groups from an external data source.

    \b
        +-------------+--------------+----------+-----------------------------+
        |  Principal  |  in Syncer?  |  in TS?  |  Result                     |
        +-------------+--------------+----------+-----------------------------+
        |    USER     |     TRUE     |   FALSE  |  [green]CREATE[/]  in  ThoughtSpot    |
        |    USER     |     TRUE     |   TRUE   |  [yellow]UPDATE[/]  in  ThoughtSpot    |
        |    USER     |     FALSE    |   FALSE  |    { no action taken }      |
        |    USER     |     FALSE    |   TRUE   |  [red]REMOVE[/] from ThoughtSpot**  |
        |---------------------------------------------------------------------|
        |    GROUP    |     TRUE     |   FALSE  |  [green]CREATE[/]  in  ThoughtSpot    |
        |    GROUP    |     TRUE     |   TRUE   |  [yellow]UPDATE[/]  in  ThoughtSpot    |
        |    GROUP    |     FALSE    |   FALSE  |    { no action taken }      |
        |    GROUP    |     FALSE    |   TRUE   |  [red]REMOVE[/] from ThoughtSpot**  |
        +-------------+--------------+----------+-----------------------------+

         * [yellow]UPDATE[/] includes GROUP reassignment, if applicable
        ** if --remove-deleted is not specified, default to { no action taken }
    """
    ts = ctx.obj.thoughtspot

    # ==================================================================================================================
    # EXPORT MODE
    # ==================================================================================================================
    
    tasks = [
        ("export_principals", "Getting existing Security Strategy"),
        ("dump_principals", f"Writing Security Strategy to {syncer.name}"),
    ]

    if export:
        with LiveTasks(tasks, console=rich_console) as tasks:
            with tasks["export_principals"]:
                if create_empty:
                    u, g, x = [], [], []
                else:
                    u, g, x = work._get_current_security(ts)

            with tasks["dump_principals"]:
                syncer.dump(users, data=u)
                syncer.dump(groups, data=g)
                syncer.dump(associations, data=x)

        raise typer.Exit()

    # ==================================================================================================================
    # IMPORT MODE
    # ==================================================================================================================
    
    tasks = [
        ("load_principals", f"Reading Security Strategy from {syncer.name}"),
        ("sync_principals", "Syncing Security Strategy to ThoughtSpot"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:

        with tasks["load_principals"]:
            u = syncer.load(users)
            g = syncer.load(groups)
            x = syncer.load(associations)

        with tasks["sync_principals"]:
            principals = work._form_principals(u, g, x)

            try:
                r = ts.api.user_sync(
                    principals=principals,
                    apply_changes=apply_changes,
                    remove_deleted=remove_deleted,
                    password=new_user_password,
                )
            except httpx.HTTPStatusError as e:
                r = e.response
                d = r.json()
                err = " ".join(json.loads(d["debug"]))

                if "password" in err.casefold():
                    log.warning(f"{err.strip()}, did you use [b cyan]--new-user-password[/]?")
                    raise typer.Exit(0)

                raise e from None

            else:
                data = r.json()

    for principal_type in ("groups", "users"):
        centered_table = layout.build_table()

        create = data[principal_type + "Added"]
        update = data[principal_type + "Updated"]
        delete = data[principal_type + "Deleted"]
        rows = it.zip_longest(create, update, delete)

        for idx, row in enumerate(rows, start=1):

            if idx < 10:
                centered_table.renderable.add_row(*row)
            elif idx == 10:
                centered_table.renderable.add_row("", "...", "", end_section=True)
            elif idx > 10:
                continue

        centered_table.renderable.title = f"Synced {principal_type.title()}"
        centered_table.renderable.footer = f"Hello world"
        rich_console.print(centered_table)
