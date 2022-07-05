from typer import Argument as A_, Option as O_
import typer

from cs_tools.cli.ux import console, CSToolsGroup


app = typer.Typer(
    cls=CSToolsGroup,
    name='tools',
    help="""
    Run an installed tool.

    Tools are a collection of scripts to perform different functions
    which aren't native to ThoughtSpot or advanced functionality for
    clients who have a well-adopted platform.
    """,
    subcommand_metavar='<tool>',
    invoke_without_command=True
)


@app.callback()
def _hidden_options(
    ctx: typer.Context,
    # Both options are completely hidden.
    private: bool = O_(False, hidden=True),
    beta: bool = O_(False, hidden=True)
):
    if ctx.invoked_subcommand is not None:
        return

    for tool_name, click_group in ctx.command.commands.items():
        cs_tool = ctx.obj.tools[tool_name]

        if private and cs_tool.privacy == 'private':
            click_group.hidden = False

        if beta and cs_tool.privacy == 'beta':
            click_group.hidden = False

    console.print(ctx.get_help())
    raise typer.Exit(code=0)
