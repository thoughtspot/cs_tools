from __future__ import annotations

from collections.abc import Coroutine
from typing import Literal
import collections
import logging
import threading
import time

from rich import console
from rich.align import Align
import httpx
import typer

from cs_tools import _types, errors, utils
from cs_tools.api import workflows
from cs_tools.cli import (
    custom_types,
    progress as px,
)
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.input import ConfirmationListener
from cs_tools.cli.tools import searchable
from cs_tools.cli.ux import AsyncTyper
from cs_tools.sync.base import Syncer

from ._utils import Group, User, determine_what_changed
from .models import PrincipalMetadataPermission

_LOG = logging.getLogger(__name__)
app = AsyncTyper(help="""Manage Users and Groups in bulk.""")


def _tick_tock(task: px.WorkTask) -> None:
    """I'm just a clock :~)"""
    while not task.finished:
        time.sleep(1)
        task.advance(step=1)


def _transform_shared(input_data):
    out = []
    for p in input_data.get("principal_permission_details", []):
        principal_id = p.get("principal_id")
        principal_name = p.get("principal_name")
        for mi in p.get("metadata_permission_info", []):
            metadata_type = mi.get("metadata_type")
            for m in mi.get("metadata_permissions", []):
                metadata_id = m.get("metadata_id") or (m.get("metadata_owner") or {}).get("id")
                metadata_name = m.get("metadata_name") or (m.get("metadata_owner") or {}).get("name")
                permission = m.get("permission")
                out.append(
                    {
                        "principal_id": principal_id,
                        "principal_name": principal_name,
                        "metadata_type": metadata_type,
                        "metadata_id": metadata_id,
                        "metadata_name": metadata_name,
                        "permission": permission,
                    }
                )
    return out


@app.command(name="transfer-sharing")
@depends_on(thoughtspot=ThoughtSpot())
def transfer_sharing(
    ctx: typer.Context,
    to_username: str = typer.Option(..., "--to", help="User to share the content."),
    from_username: str = typer.Option(..., "--from", help="Transfer content shared to current user."),
    message: str = typer.Option("Transfering Content Sharing...", "--message", help="Messge to send the target user."),
    no_prompt: bool = typer.Option(False, "--no-prompt", help="disable the confirmation prompt"),
    content: _types.UserFriendlyObjectType = typer.Option(
        None,
        help=(
            "Only content of this type will be [fg-success]selected[/]. If not specified will run for:"
            " LIVEBOARD, ANSWER, LOGICAL_TABLE values only. "
        ),
    ),
    syncer: Syncer = typer.Option(
        None,
        click_type=custom_types.Syncer(models=[PrincipalMetadataPermission]),
        help="protocol and path for options to pass to the syncer",
        show_default=False,
        rich_help_panel="Syncer Options",
    ),
    notify_on_share: bool = typer.Option(False, "--notify", help="Notify target user."),
    org_override: str = typer.Option(None, "--org", help="The Org to switch to before performing actions."),
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

    ts = ctx.obj.thoughtspot
    org_id = None
    # Switch the org
    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    if org_override is not None:
        c = ts.api.orgs_search(org_identifier=org_override)
        r = utils.run_sync(c)

        try:
            r.raise_for_status()
            _ = next(iter(r.json()))
        except StopIteration:
            raise errors.CSToolsError(f"Could not find the org '{org_id}'") from None

        org_id = _["id"]

    if from_username is None:
        raise typer.BadParameter("--from_username must be provided")

    if to_username is None:
        raise typer.BadParameter("--to_username must be provided")

    # if content not in ['LIVEBOARD','ANSWER','LOGICAL_TABLE']:
    # Extend for: ['CONNECTION', 'TABLE', 'VIEW', 'SQL_VIEW', 'MODEL', 'LIVEBOARD', 'ANSWER']
    # raise typer.BadParameter("--content is not recognized.")

    # Validate If user is admin or not.
    user_info = ts.api.users_search(guid=to_username)
    r = utils.run_sync(user_info)
    _ = r.json()
    to_user_id = _[0]["id"]

    if len(_) == 0:
        _LOG.warning(f"[fg-warn]No user with name  {to_username}.")
        return 0
    elif "ADMINISTRATION" in _[0]["org_privileges"][str(org_id)]:
        _LOG.warning(f"[fg-warn]Target User is Admin. Not required to do the sharing for user {to_username}.")
        return 0

    TOOL_TASKS = [
        px.WorkTask(id="GATHER", description="Fetching objects to share"),
        px.WorkTask(id="DUMP", description="Dumping Details"),
        px.WorkTask(id="CONFIRM", description="Confirmation for sharing to new user"),
        px.WorkTask(id="TRANSFER", description=f"Setting [fg-secondary]{to_username}[/] as the Author"),
    ]

    with px.WorkTracker(
        f"Identifying Shared Objects for [fg-secondary]{from_username}[/]", tasks=TOOL_TASKS
    ) as tracker:
        with tracker["GATHER"] as this_task:
            # security_metadata_permissions
            shared_content = []
            if content is None:
                for content in ["LIVEBOARD", "ANSWER", "LOGICAL_TABLE"]:
                    c = ts.api.security_principal_permissions(
                        guid=from_username, principal_type="USER", metadata_type=content
                    )
                    r = utils.run_sync(c)
                    _ = r.json()
                    shared_content.extend(_transform_shared(_))

            else:
                c = ts.api.security_principal_permissions(
                    guid=from_username, principal_type="USER", metadata_type=content
                )
                r = utils.run_sync(c)
                _ = r.json()
                shared_content.extend(_transform_shared(_))

        with tracker["DUMP"] as this_task:
            d = [
                PrincipalMetadataPermission.validated_init(
                    principal_id=row["principal_id"],
                    principal_name=row["principal_name"],
                    metadata_type=row["metadata_type"],
                    metadata_id=row["metadata_id"],
                    metadata_name=row["metadata_name"],
                    permission=row["permission"],
                ).model_dump()
                for row in shared_content
            ]

            syncer.dump("share_report", data=d)

        with tracker["CONFIRM"] as this_task:
            if no_prompt:
                this_task.skip()

            else:
                this_task.description = "[fg-warn]Confirmation prompt"
                this_task.total = ONE_MINUTE = 60

                tracker.extra_renderable = lambda: Align.center(
                    console.Group(
                        Align.center(f"{len(shared_content)} metadata found to be shared"),
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
                    this_task.description = "[fg-error]Denied[/] (no sharing done)"
                    return 0
                else:
                    this_task.description = f"[fg-success]Approved[/] (sharing {len(shared_content):,})"

        # Applying Sharing
        with tracker["TRANSFER"] as this_task:
            for row in shared_content:
                try:
                    c = ts.api.security_share_content(
                        principal_guid=to_user_id,
                        principal_type="USER",
                        message=message,
                        object_guid=row["metadata_id"],
                        metadata_type=row["metadata_type"],
                        share_mode=row["permission"],
                        notify_on_share=notify_on_share,
                    )
                    r = utils.run_sync(c)
                    r.raise_for_status()
                except httpx.HTTPStatusError as e:
                    logging.warning(
                        "security_share failed: principal=%s object=%s status=%s response=%s error=%s",
                        row.get("principal_id"),
                        row.get("metadata_id"),
                        getattr(e.response, "status_code", None),
                        r.json(),
                        str(e),
                    )

    return 0


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
    org_override: str = typer.Option(None, "--org", help="The Org to switch to before performing actions."),
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

    # Switch the org
    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

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
                metadata_search_options["metadata"] = [{"type": _types.lookup_metadata_type(t, mode="FRIENDLY_TO_API")} for t in ALL_TYPES]  # noqa: E501
                metadata_search_options["tag_identifiers"] = tags
                # fmt: on

            if content:
                metadata_search_options["metadata"] = [
                    {"type": _types.lookup_metadata_type(content, mode="FRIENDLY_TO_API")}
                ]

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
            _LOG.info("[fg-warn]No objects found with your input options")
            return 0

        _LOG.info(f"Found {len(filtered):,} objects to transfer to [fg-secondary]{to_username}")

        with tracker["TRANSFER"] as this_task:
            this_task.total = len(filtered)

            async def _transfer_and_advance(guid: _types.GUID) -> None:
                r = await ts.api.security_metadata_assign(guid=guid, user_identifier=to_username)
                if r.is_success:
                    this_task.advance(step=1)
                else:
                    _LOG.debug(f"Could not transfer {guid}\n{r.text}\n")

            c = utils.bounded_gather(*(_transfer_and_advance(guid=_) for _ in filtered), max_concurrent=15)
            d = utils.run_sync(c)

        _LOG.info(f"Successfully transferred {this_task.completed:,} objects to [fg-secondary]{to_username}[/]")

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
    deletion: str = typer.Option(..., help="directive to find content to delete", rich_help_panel="Syncer Options"),
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
        px.WorkTask(id="DELETE", description="Deleting Users from ThoughtSpot"),
    ]

    with px.WorkTracker("Deleting Users", tasks=TOOL_TASKS) as tracker:
        with tracker["LOAD_DATA"]:
            data = syncer.load(deletion)

            user_identifiers: set[_types.PrincipalIdentifier] = {
                row.get("user_guid", None) or row.get("username", None)
                for row in data
                if row.get("user_guid", None) or row.get("username", None)
            }

        with tracker["CONFIRM"] as this_task:
            if no_prompt:
                this_task.skip()
            else:
                this_task.description = "[fg-warn]Confirmation prompt"
                this_task.total = ONE_MINUTE = 60

                tracker.extra_renderable = lambda: Align.center(
                    console.Group(
                        Align.center(f"{len(user_identifiers):,} Users will be deleted"),
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
                    this_task.description = f"[fg-success]Approved[/] (deleting {len(user_identifiers):,})"

        with tracker["DELETE"] as this_task:
            this_task.total = len(user_identifiers)

            users_to_delete: set[_types.GUID] = user_identifiers
            delete_attempts = collections.defaultdict(int)

            async def _delete_and_advance(guid: _types.GUID) -> None:
                delete_attempts[guid] += 1
                r = await ts.api.users_delete(user_identifier=guid)

                if r.is_success or delete_attempts[guid] > 10:
                    users_to_delete.discard(guid)
                    this_task.advance(step=1)

            while users_to_delete:
                c = utils.bounded_gather(*(_delete_and_advance(guid=_) for _ in users_to_delete), max_concurrent=15)
                _ = utils.run_sync(c)

    return 0


@app.command(hidden=True)
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

    Operates on only 1 org at a time.

    \b
    Uses the [fg-warn]cs_tools tools searchable metadata[/] data model (or use [fg-warn]--export-only[/] flag to fetch).

      --delete-mode HIDE .... the principal will be set to NON_SHAREABLE and moved to a group called "HIDDEN".
      --delete-mode REMOVE .. the principal will be deleted from the system.
      --delete-mode IGNORE .. the principal will not be deleted if they do not exist in the syncer

      [fg-warn]:mage: Important!
      [fg-primary]ts_xref_principal[/] represents the relationship of [fg-primary]Principal K is a member of Group X[/].
    """
    _LOG.warning(":mage: This command is currently getting an upgrade. We'll be back soon!")
    return 0
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
        px.WorkTask(id="TS_GROUP", description="  Fetching [fg-secondary]GROUP[/] data"),
        px.WorkTask(id="TS_PRIVILEGE", description="  Fetching [fg-secondary]PRIVILEGE[/] data"),
        px.WorkTask(id="TS_USER", description="  Fetching [fg-secondary]USER[/] data"),
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

            with tracker["TS_GROUP"]:
                c = ts.api.groups_search_v1()
                r = utils.run_sync(c)
                _ = r.json()

                # c = workflows.paginator(ts.api.groups_search, record_size=150_000, timeout=60 * 15)
                # _ = utils.run_sync(c)

                # DUMP GROUP DATA
                d = searchable.api_transformer.to_group_v1(data=_, cluster=CLUSTER_UUID)
                existing[searchable.models.Group.__tablename__].extend(d)

                # DUMP GROUP->GROUP_MEMBERSHIP DATA
                d = searchable.api_transformer.to_group_membership(data=_, cluster=CLUSTER_UUID)
                existing[searchable.models.GroupMembership.__tablename__].extend(d)

            with tracker["TS_PRIVILEGE"]:
                # TODO: ROLE->PRIVILEGE DATA.
                # TODO: GROUP->ROLE DATA.

                # DUMP GROUP->PRIVILEGE DATA
                d = searchable.api_transformer.to_group_privilege(data=_, cluster=CLUSTER_UUID)
                existing[searchable.models.GroupPrivilege.__tablename__].extend(d)

            with tracker["TS_USER"]:
                c = workflows.paginator(ts.api.users_search, record_size=150_000, timeout=60 * 15)
                _ = utils.run_sync(c)

                # DUMP USER DATA
                d = searchable.api_transformer.ts_user(data=_, cluster=CLUSTER_UUID)
                existing[searchable.models.User.__tablename__].extend(d)

                # DUMP USER->GROUP_MEMBERSHIP DATA
                d = searchable.api_transformer.ts_group_membership(data=_, cluster=CLUSTER_UUID)
                # FILTER TO ONLY THE GROUPS IN THIS ORG.
                _ = {_["group_guid"] for _ in existing[searchable.models.Group.__tablename__]}
                d = [m for m in d if m["group_guid"] in _]
                existing[searchable.models.GroupMembership.__tablename__].extend(d)

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

        if delete_mode == "HIDE":
            # CREATE A GROUP CALLED HIDDEN.
            ...

        _LOG.info(
            f"[fg-secondary]Groups Info[/]\n"
            f":sparkles: [fg-success]CREATE[/] {len(g_create): >4,}\n"
            f":pencil2:  [fg-warn]UPDATE[/] {len(g_update): >4,}\n"
            f":wastebasket:  [fg-error]DELETE[/] {len(g_delete): >4,}\n"
        )

        _LOG.info(
            f"[fg-secondary]Users Info[/]\n"
            f":sparkles: [fg-success]CREATE[/] {len(u_create): >4,}\n"
            f":pencil2:  [fg-warn]UPDATE[/] {len(u_update): >4,}\n"
            f":wastebasket:  [fg-error]DELETE[/] {len(u_delete): >4,}\n"
        )

        if dry_run:
            _LOG.info(":safety_vest: DRY RUN MODE ENABLED, NO CHANGES MADE!")
            return 0

        with tracker["CONFIRM"] as this_task:
            if no_prompt:
                this_task.skip()
            else:
                this_task.description = "[fg-warn]Confirmation prompt"
                this_task.total = ONE_MINUTE = 60

                tracker.extra_renderable = lambda: Align.center(
                    console.Group(
                        Align.center("Principals will be synced to ThoughtSpot."),
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
                    this_task.description = "[fg-error]Denied[/] (no syncing done)"
                    return 0
                else:
                    this_task.description = "[fg-success]Approved[/] (syncing principals)"

        with tracker["SYNC"] as this_task:
            this_task.description = "Syncing Groups.."
            coros: list[Coroutine] = []

            # CREATE GROUPS.
            for group in {group for group in incoming["group"] if group.group_guid in g_create}:
                coros.append(
                    ts.api.groups_create(
                        name=group.group_name,
                        description=group.description,
                        display_name=group.display_name,
                        visibility=group.sharing_visibility,
                        group_type="LOCAL_GROUP",
                        privileges=list(group.privileges),
                        sub_group_identifiers=list(group.group_memberships),
                    )
                )

            if coros:
                c = utils.bounded_gather(*(coros.pop() for _ in coros[:]), max_concurrent=15)
                d = utils.run_sync(c)

            # UPDATE GROUPS.
            # if coros:
            #     c = utils.bounded_gather(*(coros.pop() for _ in coros[:]), max_concurrent=15)
            #     d = utils.run_sync(c)

            # # DELETE GROUPS.
            # if coros:
            #     c = utils.bounded_gather(*coros, max_concurrent=15)
            #     d = utils.run_sync(c)

            # this_task.description = "Syncing Users.."

            # # CREATE USERS.
            # if coros:
            #     c = utils.bounded_gather(*(coros.pop() for _ in coros[:]), max_concurrent=15)
            #     d = utils.run_sync(c)

            # # UPDATE USERS.
            # if coros:
            #     c = utils.bounded_gather(*(coros.pop() for _ in coros[:]), max_concurrent=15)
            #     d = utils.run_sync(c)

            # # DELETE USERS.
            # if coros:
            #     c = utils.bounded_gather(*coros, max_concurrent=15)
            #     d = utils.run_sync(c)

            this_task.description = "Syncing Principals.."

    return 0

    # guids_to_delete: set[_types.GUID] = {metadata_object["guid"] for metadata_object in all_metadata}
    # delete_attempts = collections.defaultdict(int)

    # async def _delete_and_advance(guid: _types.GUID) -> None:
    #     delete_attempts[guid] += 1
    #     r = await ts.api.metadata_delete(guid=guid)

    #     if r.is_success or delete_attempts[guid] > 10:
    #         guids_to_delete.discard(guid)
    #         this_task.advance(step=1)

    # while guids_to_delete:
    #     c = utils.bounded_gather(*(_delete_and_advance(guid=_) for _ in guids_to_delete), max_concurrent=15)
    #     _ = utils.run_sync(c)
