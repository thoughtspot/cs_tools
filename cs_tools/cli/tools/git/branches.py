import typer

from httpx import HTTPStatusError

from cs_tools.api._utils import UNDEFINED
from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import MultipleChoiceType
from cs_tools.cli.ux import CSToolsApp, rich_console

app = CSToolsApp(
    name="branches",
    help="Tools for working with git branches and commits.",
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
)

# consider moving to types.
VALID_METADATA_COMMIT_TYPES = ["LOGICAL_TABLE", "PINBOARD_ANSWER_BOOK", "QUESTION_ANSWER_BOOK"];


@app.command(dependencies=[thoughtspot], name="commit")
def branches_commit(
        ctx: typer.Context,
        org: str = typer.Option(None, help="the org to use if any"),
        tag: str = typer.Option(None, help="the tag for metadata to commit"),
        metadata: str = typer.Option("",
                                     custom_type=MultipleChoiceType(),
                                     help="the metadata GUIDs or names to commit"),
        branch_name: str =
        typer.Option(None,
                     help="the branch name to use for the git repository (or use the default if not provided"),
        comment: str = typer.Option(..., help="the comment to use for the commit"),
        delete_aware: bool = typer.Option(False, help="deletes content that doesn't exist in TS from the repo"),
):
    """
    Commits from ThoughtSpot to a branch in a git repository.
    """
    ts = ctx.obj.thoughtspot

    if org is not None:
        ts.org.switch(org)

    # TODO consider a check of metadata to make sure there are only the supported types.

    if tag:
        metadata_list = ts.metadata.find(tags=[tag], include_types=VALID_METADATA_COMMIT_TYPES)
        for m in metadata_list:
            rich_console.print(f"{m['id']}: {m['name']} ({m['metadata_type']})")
            metadata.append(m['id'])

    metadata_identifiers = []  # formatted for the call.
    for m in metadata:
        metadata_identifiers.append({"identifier": m})

    try:
        r = ts.api_v2.vcs_git_branches_commit(
            metadata=metadata_identifiers,
            branch_name=branch_name,
            comment=comment
        )

        if not r.is_success:
            rich_console.print(f"[bold red]Error creating the configuration: {r}.[/]")
            rich_console.print(f"[bold red]{r.content}.[/]")
        else:
            rich_console.print(r.json())

    except HTTPStatusError as e:
        rich_console.print(f"[bold red]Error creating the configuration: {e.response}.[/]")
        rich_console.print(f"[bold red]{e.response.content}.[/]")


@app.command(dependencies=[thoughtspot], name="revert-commit")
def commit_revert(
        ctx: typer.Context,
):
    """
    Reverts a commit in a git repository.
    """
    ts = ctx.obj.thoughtspot


@app.command(dependencies=[thoughtspot], name="validate")
def branches_validate(
        ctx: typer.Context,
):
    """
    Validates a branch in a git repository before doing a deploy.
    """
    ts = ctx.obj.thoughtspot


@app.command(dependencies=[thoughtspot], name="deploy")
def branches_deploy(
        ctx: typer.Context,
):
    """
    Pulls from a branch in a git repository to ThoughtSpot.
    """
    ts = ctx.obj.thoughtspot
