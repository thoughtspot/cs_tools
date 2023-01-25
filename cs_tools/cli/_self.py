import typer

from cs_tools.settings import _meta_config
from cs_tools.cli.ux import rich_console, CSToolsGroup
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import CSToolsCommand

meta = _meta_config()
app = typer.Typer(
    cls=CSToolsGroup,
    name="self",
    help=f"""
    Perform actions on CS Tools.

    {meta.newer_version_string()}
    """,
    invoke_without_command=True,
)


@app.command(cls=CSToolsCommand)
def upgrade(beta: bool = Opt(False, "--beta", help="pin your install to a pre-release build")):
    """
    Upgrade CS Tools.
    """
    raise NotImplementedError("Not yet.")


@app.command(cls=CSToolsCommand)
def uninstall(
    delete_configs: bool = Opt(False, "--delete-configs", help="delete all the configurations in CS Tools directory")
):
    """
    Remove CS Tools.
    """
    raise NotImplementedError("Not yet.")
