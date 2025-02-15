from __future__ import annotations

from typing import Literal
import json
import logging

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
        False, "--delete-aware", help="Deletes content in the GitHub repository if it is not present in this commit."
    ),
    log_errors: bool = typer.Option(False, "--log-errors", help="Log API errors to the console."),
    org_override: str = typer.Option(None, "--org", help="The org to commit objects from."),
    # === DEPRECATED ===
    branch_override: str = typer.Option(
        None,
        "-b",
        "--branch",
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

    if input_types == ["ALL"]:
        input_types = ["CONNECTION", "TABLE", "VIEW", "SQL_VIEW", "MODEL", "LIVEBOARD", "ANSWER"]  # type: ignore[assignment]

    metadata_types = {_types.lookup_metadata_type(_, mode="FRIENDLY_TO_API") for _ in input_types}

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    c = workflows.metadata.fetch_all(
        metadata_types=metadata_types,
        pattern=pattern,
        created_by_user_identifiers=authors,
        tag_identifiers=tags,
        http=ts.api,
    )
    _ = api_transformer.ts_metadata_object(data=utils.run_sync(c))

    metadata_guids: list[_types.GUID] = []

    for metadata_object in _:
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
        _ = r.json()

    except HTTPStatusError as e:
        _LOG.error(f"Could not commit {len(metadata_guids)} Objects, see logs for details..")
        _LOG.debug(f"Full error: {e}", exc_info=True)
        return 1

    else:
        _LOG.debug(f"RAW /vcs/git/branches/commit API RESPONSE:\n{json.dumps(_, indent=2)}")

    table = local_utils.TMLOperations(_["committed_files"], domain="GITHUB", op="EXPORT")

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
        "-b",
        "--branch",
        help="The name of the branch to deploy from.",
    ),
    commit_id: str = typer.Option(
        None,
        help="The specific commit to deploy, or the HEAD of the branch is used.",
    ),
    tags: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="TML will be tagged with these name(s), comma separated.",
        show_default=False,
    ),
    deploy_type: _types.TMLDeployType = typer.Option(
        "DELTA",
        help="If all TML or only modified files since the last known DEPLOY should be deployed.",
        rich_help_panel="TML Deploy Options",
    ),
    deploy_policy: _types.TMLImportPolicy = typer.Option(
        "ALL_OR_NONE",
        help="Whether to accept any errors during the DEPLOY.",
        rich_help_panel="TML Deploy Options",
    ),
    org_override: str = typer.Option(None, "--org", help="The org to deploy TML to."),
    log_errors: bool = typer.Option(False, "--log-errors", help="Log TML errors to the console."),
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
        _ = r.json()

    except HTTPStatusError as e:
        _LOG.error("Could not deploy commit, see logs for details..")
        _LOG.debug(f"Full error: {e}", exc_info=True)
        return 1

    else:
        _LOG.debug(f"RAW /vcs/git/commits/deploy API RESPONSE:\n{json.dumps(_, indent=2)}")

    table = local_utils.TMLOperations(
        _, domain="GITHUB", op="VALIDATE" if deploy_policy == "VALIDATE_ONLY" else "IMPORT", policy=deploy_policy
    )

    if ts.session_context.environment.is_ci:
        _LOG.info(table)
    else:
        RICH_CONSOLE.print(table)

    guids_to_tag: set[_types.GUID] = set()

    for response in table.statuses:
        if log_errors and response.status != "OK":
            assert response.message is not None, "TML warning/errors should always come with a raw.error_message."
            n = len(response.cleaned_messages)
            s = "" if n == 1 else "s"
            _LOG.log(
                level=logging.getLevelName(response.status),
                msg="\n".join([f"{response.metadata_guid} >> Found {n} issue{s}.\n", response.message, "\n"]),
            )

        if response.status != "ERROR":
            assert response.metadata_guid is not None, "TML errors should not produce GUIDs."
            guids_to_tag.add(response.metadata_guid)

    if tags and guids_to_tag:
        c = workflows.metadata.tag_all(guids_to_tag, tags=tags, color="#A020F0", http=ts.api)  # ThoughtSpot Purple :~)
        _ = utils.run_sync(c)

    if table.job_status == "ERROR":
        _LOG.error("One or more TMLs failed to fully deploy, check the logs or use --log-errors for more details.")
        return 1

    return 0


@app.command(name="search-commits")
@depends_on(thoughtspot=ThoughtSpot())
def commits_search(
    ctx: typer.Context,
    metadata: str = typer.Option(None, help="The name or GUID of the Object find commits for."),
    metadata_type: str = typer.Option(None, help="The metadata type to search for."),
    branch_override: str = typer.Option(
        None,
        "-b",
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
        "-b",
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
