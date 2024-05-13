from __future__ import annotations

from httpx import HTTPStatusError
from rich.align import Align
from rich.table import Table
from typing import List
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import MultipleChoiceType
from cs_tools.cli.ux import CSToolsApp, rich_console
from cs_tools.types import DeployPolicy, DeployType, GUID, MetadataIdentity

app = CSToolsApp(
    name="branches",
    help="Tools for working with git branches and commits.",
    invoke_without_command=True,
)

# consider moving to types.
VALID_METADATA_COMMIT_TYPES = ["LOGICAL_TABLE", "PINBOARD_ANSWER_BOOK", "QUESTION_ANSWER_BOOK"]


@app.command(dependencies=[thoughtspot], name="commit")
def branches_commit(
    ctx: typer.Context,
    org_override: str = typer.Option(None, "--org", help="the org to use, if any"),
    tag: str = typer.Option(None, help="the tag for metadata to commit"),
    metadata_ids: str = typer.Option("", click_type=MultipleChoiceType(), help="the metadata GUIDs or names to commit"),
    branch_name: str = typer.Option(
        None, help="the branch name to use for the git repository (or use the default if not provided"
    ),
    comment: str = typer.Option(..., help="the comment to use for the commit"),
    delete_aware: bool = typer.Option(False, help="deletes content that doesn't exist in TS from the repo"),
):
    """
    Commits from ThoughtSpot to a branch in a git repository.
    """
    ts = ctx.obj.thoughtspot

    if org_override is not None:
        ts.org.switch(org_override)

    # TODO consider a check of metadata to make sure there are only the supported types.

    if tag:
        metadata_list = ts.metadata.find(tags=[tag], include_types=VALID_METADATA_COMMIT_TYPES)
        for m in metadata_list:
            rich_console.print(f"{m['id']}: {m['name']} ({m['metadata_type']})")
            metadata_ids.append(m["id"])

    metadata_identifiers = []  # format for the call.
    for m in metadata_ids:
        metadata_identifiers.append({"identifier": m})

    try:
        r = ts.api.v2.vcs_git_branches_commit(
            metadata=metadata_identifiers,
            branch_name=branch_name,
            comment=comment,
            delete_aware=delete_aware,
        )
    except HTTPStatusError as e:
        rich_console.print(f"[b red]Error creating the configuration: {e.response}.")
        rich_console.print(f"[b red]{e.response.content}.")

    rich_console.print(r.json())


@app.command(dependencies=[thoughtspot], name="search-commits")
def commits_search(
    ctx: typer.Context,
    metadata_id: str = typer.Argument(..., help="the metadata GUID or name to search for"),
    metadata_type: str = typer.Argument(
        ..., help=f"the metadata type to search for: {', '.join(VALID_METADATA_COMMIT_TYPES)}"
    ),
    org_override: str = typer.Option(None, "--org", help="the org to use, if any"),
    branch_name: str = typer.Option(None, help="the branch name to use for the git repository or use the default"),
    record_offset: int = typer.Option(0, help="the record offset to use"),
    record_size: int = typer.Option(-1, help="the record size to use"),
):
    """
    Searches for the commits for the given metadata ID.
    """
    ts = ctx.obj.thoughtspot

    if org_override is not None:
        ts.org.switch(org_override)

    try:
        r = ts.api.v2.vcs_git_commits_search(
            metadata_identifier=metadata_id,
            metadata_type=metadata_type,
            branch_name=branch_name,
            record_offset=record_offset,
            record_size=record_size,
        )
    except HTTPStatusError as e:
        rich_console.print(f"[b red]Error finding commits for  {metadata_id}: {e}.")
        rich_console.print(f"[b red]{e.response.content}.")

    rich_console.print(r.json())


@app.command(dependencies=[thoughtspot], name="revert-commit")
def commit_revert(
    ctx: typer.Context,
    commit_id: str = typer.Argument(..., help="the commit ID to revert (found on GitHub)"),
    org_override: str = typer.Option(None, "--org", help="the org to use, if any"),
    metadata_ids: str = typer.Option(
        None, click_type=MultipleChoiceType(), help="the metadata GUIDs or names to revert"
    ),
    revert_policy: str = typer.Option("ALL_OR_NONE", help="the revert policy to use, either PARTIAL or ALL_OR_NONE"),
    branch_name: str = typer.Option(None, help="the branch name to use for the git repository or use the default"),
):
    """
    Reverts a commit in a git repository.
    """
    ts = ctx.obj.thoughtspot

    valid_policies = ["PARTIAL", "ALL_OR_NONE"]
    if revert_policy not in valid_policies:
        rich_console.log(f"[b red]Invalid revert policy: {revert_policy}.  Must be one of {', '.join(valid_policies)}")
        raise typer.Exit(1)

    if org_override is not None:
        ts.org.switch(org_override)

    metadata_identifiers = None  # format for the call.
    if metadata_ids:
        metadata_identifiers = []  # format for the call.
        for m in metadata_ids:
            metadata_identifiers.append({"identifier": m})

    try:
        r = ts.api.v2.vcs_git_commits_id_revert(
            commit_id=commit_id,
            metadata=metadata_identifiers,
            branch_name=branch_name,
            revert_policy=revert_policy,
        )
    except HTTPStatusError as e:
        rich_console.print(f"[b red]Error reverting commit {commit_id}: {e.response}.")
        rich_console.print(f"[b red]{e.response.content}.")

    rich_console.print(r.json())


@app.command(dependencies=[thoughtspot], name="validate")
def branches_validate(
    ctx: typer.Context,
    source_branch: str = typer.Argument(..., help="the source branch to use"),
    target_branch: str = typer.Argument(..., help="the target branch to use"),
    org_override: str = typer.Option(None, "--org", help="the org to use, if any"),
):
    """
    Validates a branch in a git repository before merging.
    """
    ts = ctx.obj.thoughtspot

    if org_override is not None:
        ts.org.switch(org_override)

    try:
        ts.api.v2.vcs_git_branches_validate(source_branch_name=source_branch, target_branch_name=target_branch)
    except HTTPStatusError as e:
        rich_console.print(f"[b red]Error validating {source_branch} to {target_branch}: {e}.")
        rich_console.print(f"[b red]{e.response.content}.")

    rich_console.print("[bold green]Validation successful.  Ok to deploy.")


@app.command(dependencies=[thoughtspot], name="deploy")
def branches_deploy(
    ctx: typer.Context,
    org_override: str = typer.Option(None, "--org", help="the org to use, if any"),
    commit_id: str = typer.Option(None, help="the commit ID to deploy or none for latest"),
    branch_name: str = typer.Option(None, help="the branch name to use, or default"),
    deploy_type: str = typer.Option("DELTA", help="the deploy type to use, either DELTA or FULL"),
    deploy_policy: str = typer.Option("ALL_OR_NONE", help="the deploy policy to use, either PARTIAL or ALL_OR_NONE"),
    tags: list[str] = typer.Option([], help="one or more tags to add to the imported content"),
):
    """
    Pulls from a branch in a git repository to ThoughtSpot.
    """
    ts = ctx.obj.thoughtspot

    if org_override is not None:
        ts.org.switch(org_override)

    try:
        r = ts.api.v2.vcs_git_commits_deploy(
            commit_id=commit_id,
            branch_name=branch_name,
            deploy_type=DeployType.full if deploy_type == "FULL" else DeployType.delta,
            deploy_policy=DeployPolicy.all_or_none if deploy_policy == "ALL_OR_NONE" else DeployPolicy.partial,
        )
    except HTTPStatusError as e:
        rich_console.print(f"[b red]Error deploying: {e}.")
        rich_console.print(f"[b red]{e.response.content}.")

    # An OK response doesn't mean the content was successful.
    results = r.json()

    table = Table(title="Deploy Results", width=135)
    table.add_column("File Name", width=25)
    table.add_column("Status", width=10)
    table.add_column("Message", width=100)

    guids = []
    for _ in results:
        try:
            guids.append(_["file_name"].split(".")[0])
        except Exception as e:
            rich_console.print(f"[b red]Error getting GUID for {_['file_name']}:  {e}")
        table.add_row(_["file_name"], _["status_code"], _["status_message"])

    rich_console.print(Align.center(table))

    _add_tags(ts=ts, objects=guids, tags=tags)


def _add_tags(ts: thoughtspot.ThoughtSpot, objects: list[GUID], tags: list[str]) -> None:
    """
    Adds the tags to the items in the response.
    :param ts: The ThoughtSpot object.
    :param objects: List of the objects to add the tags to.
    :param tags: List of tags to create.
    """
    with rich_console.status(f"[bold green]adding tags: {tags}[/]"):
        metadata: List[MetadataIdentity] = []
        for guid in objects:
            metadata.append({"identifier": guid})

        if metadata and tags:  # might all be errors
            rich_console.print(f"Adding tags {tags} to {objects}")
            try:
                ts.api.v2.tags_assign(metadata=metadata, tag_identifiers=tags)
            except HTTPStatusError as e:
                rich_console.error(f"Error adding tags {tags} for metadata {objects}. Error: {e}")

