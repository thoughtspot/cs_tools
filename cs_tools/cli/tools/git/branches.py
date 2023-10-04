import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.ux import CSToolsApp

app = CSToolsApp(
    name="branches",
    help="Tools for working with git branches and commits.",
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
)

@app.command(dependencies=[thoughtspot], name="commit")
def branches_commit(
        ctx: typer.Context,
):
    """
    Commits from ThoughtSpot to a branch in a git repository.
    """
    ts = ctx.obj.thoughtspot

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
