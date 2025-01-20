from __future__ import annotations

from typing import Literal
import collections
import logging
import time

import typer

from cs_tools import _types, errors, utils
from cs_tools.api import workflows
from cs_tools.cli import (
    custom_types,
    progress as px,
)
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.tools import searchable
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper
from cs_tools.sync.base import Syncer

from ._utils import Group, User, determine_what_changed

log = logging.getLogger(__name__)
app = AsyncTyper(help="""Manage Users and Groups in bulk.""")


def _tick_tock(task: px.WorkTask) -> None:
    """I'm just a clock :~)"""
    while not task.finished:
        time.sleep(1)
        task.advance(step=1)


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def transfer(
    ctx: typer.Context,
    to_username: str = typer.Option(..., "--to", help="User to assign as the Author of content."),
    from_username: str = typer.Option(None, "--from", help="If provided, only transfer content owned by this user."),
    content: _types.UserFriendlyObjectType = typer.Option(
        None,
        help=(
            "Only content of this type will be [fg-success]selected[/] [fg-warn]if used alone, you must also specify "
            "--from[/]."
        ),
    ),
    tags: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="Content with any of these tags (case sensitive) will be [fg-success]selected[/], comma separated",
    ),
    guids: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="Content with any of these guids will be [fg-success]selected[/], comma separated",
    ),
):
    """
    Ensure objects are owned by a User.

    Content may be selected in AND fashion based on the following..
    \b
        - Current Owner
        - Metadata Type
        - Tag
        - Indvidual GUID

    ..ALL objects must match the selection criteria to be moved to the new owner.
    """
    if all(x is None for x in (from_username, tags, content, guids)):
        raise typer.BadParameter("at least one of --from, --tags, --content, or --guids must be provided")
    if content is not None and all(x is None for x in (from_username, tags, guids)):
        raise typer.BadParameter("at least one of --from, --tags, or --guids must be provided when using --content")

    ts = ctx.obj.thoughtspot

    TOOL_TASKS = [
        px.WorkTask(id="GATHER", description="Fetching objects to transfer"),
        px.WorkTask(id="TRANSFER", description=f"Setting [fg-secondary]{to_username}[/] as the Author"),
    ]

    with px.WorkTracker("Transferring ownership of Content", tasks=TOOL_TASKS) as tracker:
        ALL_TYPES = ["CONNECTION", "LOGICAL_TABLE", "LIVEBOARD", "ANSWER"]

        with tracker["GATHER"]:
            metadata_search_options = {}

            if tags:
                # fmt: off
                metadata_search_options["metadata"] = [{"type": _types.lookup_api_type(t, mode="FRIENDLY")} for t in ALL_TYPES]  # noqa: E501
                metadata_search_options["tag_identifiers"] = tags
                # fmt: on

            if content:
                metadata_search_options["metadata"] = [{"type": _types.lookup_api_type(content, mode="FRIENDLY")}]

            if guids:
                metadata_search_options["metadata"] = [{"identifier": guid} for guid in guids]

            if not metadata_search_options:
                c = workflows.metadata.fetch_all(metadata_types=ALL_TYPES, http=ts.api)
            else:
                c = workflows.utils.paginator(ts.api.metadata_search, guid="", **metadata_search_options)

            d = utils.run_sync(c)

            if content:
                _ = {
                    "TABLE": "ONE_TO_ONE_LOGICAL",
                    "VIEW": "AGGR_WORKSHEET",
                    "SQL_VIEW": "SQL_VIEW",
                    "MODEL": "WORKSHEET",
                    "CONNECTION": "CONNECTION",
                    "LIVEBOARD": "LIVEBOARD",
                    "ANSWER": "ANSWER",
                }
                d = [m for m in d if _[content.upper()] in (m["metadata_type"], m["metadata_header"].get("type"))]

            if from_username:
                d = [m for m in d if m["metadata_header"]["authorName"] == from_username]

            filtered = [m["metadata_id"] for m in d]

        if not filtered:
            log.info("[fg-warn]No objects found with your input options")
            return 0

        log.info(f"Found {len(filtered):,} objects to transfer to [fg-secondary]{to_username}")

        with tracker["TRANSFER"] as this_task:
            this_task.total = len(filtered)

            async def _transfer_and_advance(guid: _types.GUID) -> None:
                r = await ts.api.security_metadata_assign(guid=guid, user_identifier=to_username)
                if r.is_success:
                    this_task.advance(step=1)
                else:
                    log.debug(f"Could not transfer {guid}\n{r.text}\n")

            c = utils.bounded_gather(*(_transfer_and_advance(guid=_) for _ in filtered), max_concurrent=15)
            d = utils.run_sync(c)

        log.info(f"Successfully transferred {this_task.completed:,} objects to [fg-secondary]{to_username}[/]")

    return 0


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def delete(
    ctx: typer.Context,
    syncer: Syncer = typer.Option(
        ...,
        click_type=custom_types.Syncer(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    no_prompt: bool = typer.Option(False, "--no-prompt", help="disable the confirmation prompt"),
) -> _types.ExitCode:
    """
    Remove Users (only) from ThoughtSpot.

    This command will perform an equivalent operation to a "sync --delete-mode REMOVE" command.

    Your syncer should contain at least one of the following fields.

    \b
        +--------------------------------------+----------------+
        |              user_guid               |    username    |
        +--------------------------------------+----------------+
        | 00000841-3bd9-f6bb-d7c9-7fb4322d08ad | cs_tools       |
        | c209661c-fba2-4a64-8a24-2d70a50a0b2c | namey.namerson |
        | 00000841-3bd9-c107-4236-eeb790882a55 | fake.user      |
        +--------------------------------------+----------------+
    """
    ts = ctx.obj.thoughtspot

    if not ts.session_context.user.is_admin:
        raise errors.InsufficientPrivileges(
            user=ts.session_context.user,
            service="the users/create API",
            required_privileges=[_types.GroupPrivilege.can_administer_thoughtspot],
        )

    TOOL_TASKS = [
        px.WorkTask(id="LOAD_DATA", description=f"Loading data from {syncer.name}"),
        px.WorkTask(id="CONFIRM", description="Confirmation Prompt"),
        px.WorkTask(id="DELETE", description="Syncing Principals to ThoughtSpot"),
    ]

    return 0


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def sync(
    ctx: typer.Context,
    syncer: Syncer = typer.Option(
        ...,
        click_type=custom_types.Syncer(models=[searchable.models.PRINCIPAL_MODELS]),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    export_only: bool = typer.Option(False, "--export-only", help="Export all principals instead of syncing."),
    delete_mode: Literal["HIDE", "REMOVE", "IGNORE"] = typer.Option(
        "IGNORE", help="How to handle a principal if it does not exist in the syncer, but does in ThoughtSpot."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Test your Sync without making any changes."),
    no_prompt: bool = typer.Option(False, "--no-prompt", help="Disable the confirmation prompt."),
    org_override: str = typer.Option(0, "--org", help="The org to sync principals in."),
):
    """
    Sync your principals (Users, Groups, Memberships) from an external data source.

    \b
    Uses the [fg-warn]cs_tools tools searchable metadata[/] data model (or use [fg-warn]--export-only[/] flag to fetch).

      --delete-mode HIDE .... the principal will be set to NON_SHAREABLE and moved to a group called "HIDDEN".
      --delete-mode REMOVE .. the principal will be deleted from the system.
      --delete-mode IGNORE .. the principal will not be deleted if they do not exist in the syncer

      [fg-warn]:mage: Important!
      [fg-primary]ts_xref_principal[/] represents the relationship of [fg-primary]Principal K is a member of Group X[/].
    """
    ts = ctx.obj.thoughtspot

    if ts.session_context.thoughtspot.is_orgs_enabled:
        org = ts.switch_org(org_id=org_override)
        org_override = org["id"]

    if not ts.session_context.user.is_admin:
        raise errors.InsufficientPrivileges(
            user=ts.session_context.user,
            service="the users/create API",
            required_privileges=[_types.GroupPrivilege.can_administer_thoughtspot],
        )

    TOOL_TASKS = [
        px.WorkTask(id="GATHER", description="Fetching Principals"),
        px.WorkTask(id="TS_ORG", description="  Fetching [fg-secondary]ORG[/] data"),
        px.WorkTask(id="TS_USER", description="  Fetching [fg-secondary]USER[/] data"),
        px.WorkTask(id="TS_GROUP", description="  Fetching [fg-secondary]GROUP[/] data"),
        px.WorkTask(id="TS_PRIVILEGE", description="  Fetching [fg-secondary]PRIVILEGE[/] data"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {syncer.name}"),
        px.WorkTask(id="LOAD_DATA", description=f"Loading data from {syncer.name}"),
        px.WorkTask(id="CONFIRM", description="Confirmation Prompt"),
        px.WorkTask(id="SYNC", description="Syncing Principals to ThoughtSpot"),
    ]

    where = "from" if export_only else "to"

    with px.WorkTracker(f"Syncing principals {where} ThoughtSpot", tasks=TOOL_TASKS) as tracker:
        existing = collections.defaultdict(list)
        incoming = collections.defaultdict(list)

        with tracker["GATHER"]:
            # DEV NOTE: @boonhapus, 2025/01/18
            #   This is identical to the flow in cs_tools.cli.tools.searchable.app.metadata
            CLUSTER_UUID = ts.session_context.thoughtspot.cluster_id

            with tracker["TS_ORG"]:
                if not ts.session_context.thoughtspot.is_orgs_enabled:
                    _ = [{"id": 0, "name": "ThoughtSpot", "description": "Your cluster is not orgs enabled."}]
                else:
                    c = ts.api.orgs_search()
                    r = utils.run_sync(c)
                    _ = r.json()

                # DUMP ORG DATA
                d = searchable.api_transformer.ts_org(data=_, cluster=CLUSTER_UUID)
                existing[searchable.models.Org.__tablename__].extend(d)

            with tracker["TS_USER"]:
                c = workflows.paginator(ts.api.users_search, record_size=150_000, timeout=60 * 15)
                _ = utils.run_sync(c)

                # DUMP USER DATA
                d = searchable.api_transformer.ts_user(data=_, cluster=CLUSTER_UUID)
                existing[searchable.models.User.__tablename__].extend(d)

                # DUMP USER->ORG_MEMBERSHIP DATA
                d = searchable.api_transformer.ts_org_membership(data=_, cluster=CLUSTER_UUID)
                existing[searchable.models.OrgMembership.__tablename__].extend(d)

                # DUMP USER->GROUP_MEMBERSHIP DATA
                d = searchable.api_transformer.ts_group_membership(data=_, cluster=CLUSTER_UUID)
                existing[searchable.models.GroupMembership.__tablename__].extend(d)

            with tracker["TS_GROUP"]:
                c = workflows.paginator(ts.api.groups_search, record_size=150_000, timeout=60 * 15)
                _ = utils.run_sync(c)

                # DUMP GROUP DATA
                d = searchable.api_transformer.ts_group(data=_, cluster=CLUSTER_UUID)
                existing[searchable.models.Group.__tablename__].extend(d)

                # DUMP GROUP->GROUP_MEMBERSHIP DATA
                d = searchable.api_transformer.ts_group_membership(data=_, cluster=CLUSTER_UUID)
                existing[searchable.models.GroupMembership.__tablename__].extend(d)

            with tracker["TS_PRIVILEGE"]:
                # TODO: ROLE->PRIVILEGE DATA.
                # TODO: GROUP->ROLE DATA.

                # DUMP GROUP->PRIVILEGE DATA
                d = searchable.api_transformer.ts_group_privilege(data=_, cluster=CLUSTER_UUID)
                existing[searchable.models.GroupPrivilege.__tablename__].extend(d)

        if export_only:
            with tracker["DUMP_DATA"]:
                for tablename, data in existing.items():
                    syncer.dump(tablename, data=data)
            return 0

        else:
            with tracker["LOAD_DATA"]:
                for tablename, _ in existing.items():
                    incoming[tablename] = syncer.load(tablename)

        # CALCULATE THE DIFF ON GROUPS.
        existing["group"] = [Group.from_syncer_info(g, org=org_override, info=existing) for g in existing["ts_group"]]
        incoming["group"] = [Group.from_syncer_info(g, org=org_override, info=incoming) for g in incoming["ts_group"]]
        g_create, g_update, g_delete = determine_what_changed(existing["group"], incoming["group"], key="group_guid")

        # fmt: off
        # CALCULATE THE DIFF ON USERS.
        existing["user"] = [User.from_syncer_info(u, deleted_groups=g_delete, org=org_override, info=existing) for u in existing["ts_user"]]  # noqa: E501
        incoming["user"] = [User.from_syncer_info(u, deleted_groups=g_delete, org=org_override, info=incoming) for u in incoming["ts_user"]]  # noqa: E501
        u_create, u_update, u_delete = determine_what_changed(existing["user"], incoming["user"], key="user_guid")
        # fmt: on

        for group_guid in g_update:
            group = next(g for g in existing["group"] if g.group_guid == group_guid)
            RICH_CONSOLE.print(group)

        if delete_mode == "HIDE":
            # CREATE A GROUP CALLED HIDDEN.
            ...

        if dry_run:
            RICH_CONSOLE.print("DRY RUN MODE ENABLED, NO CHANGES MADE.")

            RICH_CONSOLE.print(
                f"Created Groups: {len(g_create)=:,}",
                f"Updated Groups: {len(g_update)=:,}",
                f"Deleted Groups: {len(g_delete)=:,}",
            )

            RICH_CONSOLE.print(
                f"Created Users: {len(u_create)=:,}",
                f"Updated Users: {len(u_update)=:,}",
                f"Deleted Users: {len(u_delete)=:,}",
            )
            return 0

        with tracker["CONFIRM"] as this_task:
            if no_prompt:
                this_task.skip()
            else:
                this_task.description = "[fg-warn]Confirmation prompt"
                this_task.total = ONE_MINUTE = 60

                tracker.extra_renderable = lambda: Align.center(
                    console.Group(
                        Align.center(f"{len(all_metadata):,} objects will be deleted"),
                        "\n[fg-warn]Press [fg-success]Y[/] to proceed, or [fg-error]n[/] to cancel.",
                    )
                )

                th = threading.Thread(target=_tick_tock, args=(this_task,))
                th.start()

                kb = ConfirmationListener(timeout=ONE_MINUTE)
                kb.run()

                assert kb.response is not None, "ConfirmationListener never got a response."

                tracker.extra_renderable = None
                this_task.final()

                if kb.response.upper() == "N":
                    this_task.description = "[fg-error]Denied[/] (no deleting done)"
                    return 0
                else:
                    this_task.description = f"[fg-success]Approved[/] (deleting {len(all_metadata):,})"

    return 0
