from __future__ import annotations

from typing import Literal
import itertools as it
import logging
import pathlib

from httpx import HTTPStatusError
import typer

from cs_tools import _types, utils
from cs_tools.api import workflows
from cs_tools.cli import custom_types
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.tools.scriptability import (
    api_transformer,
    utils as local_utils,
)
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper

_LOG = logging.getLogger(__name__)
app = AsyncTyper(
    name="branches",
    help="Manage commits in your configured GitHub repositories.",
)


@app.command(name="commit")
@depends_on(thoughtspot=ThoughtSpot())
def branches_commit(
    ctx: typer.Context,
    input_types: custom_types.MultipleInput = typer.Option(
        ...,
        "--metadata-types",
        click_type=custom_types.MultipleInput(
            choices=["CONNECTION", "TABLE", "VIEW", "SQL_VIEW", "MODEL", "LIVEBOARD", "ANSWER", "__ALL__"],
        ),
        help="The type of Object(s) to export, comma separated.",
        rich_help_panel="Metadata Fetching Options",
    ),
    pattern: str = typer.Option(
        None,
        help=r"Object names which meet a pattern, follows SQL LIKE operator (% as a wildcard).",
        rich_help_panel="Metadata Fetching Options",
    ),
    authors: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="Objects created by these User(s), comma separated.",
        show_default=False,
        rich_help_panel="Metadata Fetching Options",
    ),
    tags: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="Objects tagged with these name(s), comma separated.",
        show_default=False,
        rich_help_panel="Metadata Fetching Options",
    ),
    include_system_owned_content: bool = typer.Option(
        False,
        "--include-system",
        help="Whether or not to include content owned by built-in Administrator accounts.",
        rich_help_panel="Metadata Fetching Options",
    ),
    commit_message: str = typer.Option(
        ...,
        "-m",
        "--comment",
        help="the comment to use for the commit",
    ),
    delete_aware: bool = typer.Option(
        False, "--delete-aware", help="deletes content that doesn't exist in TS from the repo"
    ),
    log_errors: bool = typer.Option(False, "--log-errors", help="Log API errors to the console."),
    org_override: str = typer.Option(None, "--org", help="The org to commit objects from."),
    # === DEPRECATED ===
    branch_override: str = typer.Option(
        None,
        "--branch",
        "--branch-name",
        help="The name of the branch to commit to. (configure your repository with commit_branch_name)",
        hidden=True,
    ),
):
    """Commits from ThoughtSpot to a branch in a GitHub repository."""
    # DEV NOTE: @boonhapus, 2025/02/11
    #   This tool should operate as closely as possible to scriptability.checkpoint, as
    #   they are intended to be used in the same way but have potentially different
    #   destinations (scriptability -> arbitrary file structre :: git -> GitHub).
    ts = ctx.obj.thoughtspot

    if branch_override is not None:
        _LOG.warning(
            "--branch-name is [fg-warn]deprecated[/] and may lead to unexpected behavior. "
            "Configure your ThoughtSpot<->GitHub integration with [fg-secondary]commit_branch_name[/] instead."
        )

    SYSTEM_USER_GUIDS = ts.session_context.thoughtspot.system_users.values()

    CLI_TYPES_TO_API_TYPES: dict[str, list[_types.MetadataObjectType]] = {
        "ALL": ["CONNECTION", "LOGICAL_TABLE", "LIVEBOARD", "ANSWER"],
        "CONNECTION": ["CONNECTION"],
        "TABLE": ["LOGICAL_TABLE"],
        "VIEW": ["LOGICAL_TABLE"],
        "SQL_VIEW": ["LOGICAL_TABLE"],
        "MODEL": ["LOGICAL_TABLE"],
        "LIVEBOARD": ["LIVEBOARD"],
        "ANSWER": ["ANSWER"],
    }

    metadata_types = set(it.chain.from_iterable(CLI_TYPES_TO_API_TYPES[_] for _ in input_types))

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    c = workflows.metadata.fetch_all(
        metadata_types=metadata_types,
        pattern=pattern,
        created_by_user_identifiers=authors,
        tag_identifiers=tags,
        http=ts.api,
    )
    d = api_transformer.ts_metadata_object(data=utils.run_sync(c))

    metadata_guids: list[_types.GUID] = []

    for metadata_object in d:
        if not local_utils.is_allowed_object(
            metadata_object,
            allowed_types=input_types,
            disallowed_system_users=[] if include_system_owned_content else SYSTEM_USER_GUIDS,
        ):
            continue

        metadata_guids.append(metadata_object["object_guid"])

    if not metadata_guids:
        _LOG.info("No objects found to commit.")
        return 0

    try:
        c = ts.api.vcs_git_branches_commit(
            guids=metadata_guids,
            commit_message=commit_message,
            delete_aware=delete_aware,
            branch_name=branch_override,
        )
        r = utils.run_sync(c)
        r.raise_for_status()

    except HTTPStatusError as e:
        _LOG.error(f"Could not commit {len(metadata_guids)} Objects, see logs for details..")
        _LOG.debug(f"Full error: {e}", exc_info=True)
        return 1

    # === CONFORM THE API RESPONSE TO metadata/tml/export RESPONE PAYLOAD \\
    #
    d = []

    for committed in r.json()["committed_files"]:
        # FORMAT: table/TS_DATA_SOURCE.2b7e3ebe-ee63-425c-824f-f09c0028e2b3.table.tml
        fp = pathlib.Path(committed["file_name"])

        metadata_guid = fp.suffixes[0].replace(".", "")
        metadata_name = fp.name.replace("".join(fp.suffixes), "")
        metadata_type = fp.suffixes[1].replace(".", "")

        # THESE ARE NOT SEMANTICALLY WARNINGS.....
        if _GOOFY_WARNING_STATUS := ("File not committed" in committed["status_message"]):
            committed["status_code"] = "OK"

        d.append(
            {
                "edoc": None,
                "info": {  # type: ignore
                    "id": metadata_guid,
                    "name": metadata_name,
                    "type": metadata_type,
                    "status": {
                        "status_code": committed["status_code"],
                        "error_message": committed["status_message"],
                    },
                },
            }
        )
    # === //

    table = local_utils.TMLOperations(data=d, domain="GITHUB", op="EXPORT")

    if ts.session_context.environment.is_ci:
        _LOG.info(table)
    else:
        RICH_CONSOLE.print(table)

    for response in table.statuses:
        if log_errors and response.status != "OK":
            assert response.message is not None, "TML warning/errors should always come with a raw.error_message."
            _LOG.log(
                level=logging.getLevelName(response.status),
                msg=" - ".join([response.metadata_guid, response.message]),
            )

    if table.job_status != "OK":
        _LOG.error("One or more TMLs failed to fully export, check the logs or use --log-errors for more details.")
        return 1

    return 0


@app.command(name="validate")
@depends_on(thoughtspot=ThoughtSpot())
def branches_validate(
    ctx: typer.Context,
    source: str = typer.Option(..., "--source-branch", help="The source branch to merge from."),
    target: str = typer.Option(..., "--target-branch", help="The target branch to merge into."),
    org_override: str = typer.Option(None, "--org", help="The source Org to use when comparing branches."),
):
    """Validates that your GitHub branches can be merged."""
    ts = ctx.obj.thoughtspot

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    try:
        c = ts.api.vcs_git_branches_validate(source_branch_name=source, target_branch_name=target)
        r = utils.run_sync(c)
        r.raise_for_status()

    except HTTPStatusError as e:
        _LOG.error("Could not validate branches, see logs for details..")
        _LOG.debug(f"Full error: {e}", exc_info=True)
        return 1

    else:
        _LOG.info("Branches validated successfully!")

    return 0


@app.command(name="deploy")
@depends_on(thoughtspot=ThoughtSpot())
def branches_deploy(
    ctx: typer.Context,
    branch_override: str = typer.Option(
        ...,
        "--branch",
        "--branch-name",
        help="The name of the branch to deploy from.",
    ),
    commit_id: str = typer.Option(None, help="The specific commit to deploy, or the HEAD of the branch is used."),
    tags: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="TML will be tagged with these name(s), comma separated.",
        show_default=False,
    ),
    deploy_type: _types.TMLDeployType = typer.Option(
        "DELTA",
        help="If all TML or only modified files since the last known DEPLOY should be deployed.",
    ),
    deploy_policy: _types.TMLImportPolicy = typer.Option(
        "ALL_OR_NONE",
        help="Whether to accept any errors during the DEPLOY.",
    ),
    org_override: str = typer.Option(None, "--org", help="the org to use, if any"),
):
    """Pulls from a branch in a GitHub repository to ThoughtSpot."""
    ts = ctx.obj.thoughtspot

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    try:
        c = ts.api.vcs_git_commits_deploy(
            branch_name=branch_override,
            commit_id=commit_id,
            deploy_type=deploy_type,
            deploy_policy=deploy_policy,
        )
        r = utils.run_sync(c)
        r.raise_for_status()

    except HTTPStatusError as e:
        _LOG.error("Could not deploy commit, see logs for details..")
        _LOG.debug(f"Full error: {e}", exc_info=True)
        return 1

    oper_ = "VALIDATE" if deploy_policy == "VALIDATE_ONLY" else "IMPORT"

    RICH_CONSOLE.print(r.json())
    return 1

    # === CONFORM THE API RESPONSE TO metadata/tml/export RESPONE PAYLOAD \\
    #
    d: list[local_utils.TMLStatus] = []

    for deployed in r.json():
        # FORMAT: table/TS_DATA_SOURCE.2b7e3ebe-ee63-425c-824f-f09c0028e2b3.table.tml
        fp = pathlib.Path(deployed["file_name"])

        metadata_guid = fp.suffixes[0].replace(".", "")
        metadata_name = fp.name.replace("".join(fp.suffixes), "")
        metadata_type = fp.suffixes[1].replace(".", "")

        d.append(
            local_utils.TMLStatus(
                operation=oper_,
                edoc=None,
                metadata_guid=metadata_guid,
                metadata_name=metadata_name,
                metadata_type=metadata_type,
                status=deployed["status_code"],
                message=deployed["status_message"],
                _raw=deployed,
            )
        )
    # === //

    table = local_utils.TMLOperations(statuses=d, domain="GITHUB", op=oper_, policy=deploy_policy)

    if ts.session_context.environment.is_ci:
        _LOG.info(table)
    else:
        RICH_CONSOLE.print(table)

    # guids_to_tag: set[_types.GUID] = set()
    #
    # for original_guid, response in zip(tmls, table.statuses):
    #     if log_errors and response.status != "OK":
    #         assert response.message is not None, "TML warning/errors should always come with a raw.error_message."
    #         _LOG.log(
    #             level=logging.getLevelName(response.status),
    #             msg=" - ".join([str(response.metadata_guid), response.message]),
    #         )
    #
    #     if table.can_map_guids and response.status != "ERROR":
    #         assert response.metadata_guid is not None, "TML errors should not produce GUIDs."
    #         mapping_info.map_guid(old=original_guid, new=response.metadata_guid, disallow_overriding=True)
    #         guids_to_tag.add(response.metadata_guid)

    return 0


@app.command(name="search-commits")
@depends_on(thoughtspot=ThoughtSpot())
def commits_search(
    ctx: typer.Context,
    metadata: str = typer.Option(None, help="The name or GUID of the Object find commits for."),
    metadata_type: str = typer.Option(None, help="The metadata type to search for."),
    branch_override: str = typer.Option(
        None,
        "--branch",
        "--branch-name",
        help="The name of the branch to search.",
    ),
    org_override: str = typer.Option(None, "--org", help="The org to search commit from."),
):
    """Searches for the commits for the given metadata ID."""
    ts = ctx.obj.thoughtspot

    _LOG.warning("Searching for commits via the CLI is deprecated. Visit the UI with your metadata GUID.")

    RICH_CONSOLE.print(
        f"\n"
        f"{ts.session_context.thoughtspot.url}/#/develop/api/rest/playgroundV2_0"
        f"?apiResourceId=http/api-endpoints/version-control/search-commits",
        justify="center",
    )

    return 0


@app.command(name="revert-commit")
@depends_on(thoughtspot=ThoughtSpot())
def commit_revert(
    ctx: typer.Context,
    commit_id: str = typer.Option(None, help="the commit ID to revert (found on GitHub)"),
    metadata: str = typer.Option(None, help="The name or GUID of the Object find commits for."),
    revert_policy: Literal["PARTIAL", "ALL_OR_NONE"] = typer.Option("ALL_OR_NONE", help="The revert policy to use."),
    branch_override: str = typer.Option(
        None,
        "--branch",
        "--branch-name",
        help="The name of the branch to search.",
    ),
    org_override: str = typer.Option(None, "--org", help="The org to revert the commit from."),
):
    """Searches for the commits for the given metadata ID."""
    ts = ctx.obj.thoughtspot

    _LOG.warning("Reverting commits via the CLI is deprecated. Visit the UI with your commitish.")

    RICH_CONSOLE.print(
        f"\n"
        f"{ts.session_context.thoughtspot.url}/#/develop/api/rest/playgroundV2_0"
        f"?apiResourceId=http/api-endpoints/version-control/revert-commit",
        justify="center",
    )

    return 0


# def _add_tags(ts: thoughtspot.ThoughtSpot, objects: list[GUID], tags: list[str]) -> None:
#     """
#     Adds the tags to the items in the response.
#     :param ts: The ThoughtSpot object.
#     :param objects: List of the objects to add the tags to.
#     :param tags: List of tags to create.
#     """
#     with rich_console.status(f"[bold green]adding tags: {tags}[/]"):
#         metadata: list[MetadataIdentity] = []
#         for guid in objects:
#             metadata.append({"identifier": guid})

#         if metadata and tags:  # might all be errors
#             rich_console.print(f"Adding tags {tags} to {objects}")
#             try:
#                 ts.api.v2.tags_assign(metadata=metadata, tag_identifiers=tags)
#             except HTTPStatusError as e:
#                 rich_console.error(f"Error adding tags {tags} for metadata {objects}. Error: {e}")
