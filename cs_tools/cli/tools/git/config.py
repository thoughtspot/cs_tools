import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.ux import CSToolsApp

app = CSToolsApp(
    name="config",
    help="Tools for working with git configurations.",
    add_completion=False,
    invoke_without_command=True,
    no_args_is_help=True,
)

@app.command(dependencies=[thoughtspot], name="create")
def config_create(
        ctx: typer.Context,
):
    """
    Creates a configuration for a cluster or org.  An org can only have a single configuration.
    """
    ts = ctx.obj.thoughtspot

@app.command(dependencies=[thoughtspot], name="update")
def config_update(
        ctx: typer.Context,
):
    """
    Updates a configuration for a cluster or org.
    """
    ts = ctx.obj.thoughtspot

@app.command(dependencies=[thoughtspot], name="search")
def config_search(
        ctx: typer.Context,
):
    """
    Searches for configurations.
    """
    ts = ctx.obj.thoughtspot

@app.command(dependencies=[thoughtspot], name="delete")
def config_delete(
        ctx: typer.Context,
):
    """
    Deletes a configuration for a cluster or org.
    """
    ts = ctx.obj.thoughtspot
