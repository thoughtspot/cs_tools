from typer import Argument as A_, Option as O_
import click
import typer

from cs_tools.cli.ux import console, CSToolsGroup


def _show_hidden_tool_options(
    private: bool=O_(False, '--private', hidden=True)
):
    """
    Care for the hidden options.
    """
    ctx = click.get_current_context()

    if ctx.invoked_subcommand:
        return

    if private:
        unhidden_cmds = {}

        for name, command in ctx.command.commands.items():
            if name == '__example_app__':
                continue

            command.hidden = False
            unhidden_cmds[name] = command

        ctx.command.commands = unhidden_cmds

    console.print(ctx.get_help())
    raise typer.Exit(code=0)


app = typer.Typer(
    cls=CSToolsGroup,
    name='tools',
    help="""
    Run an installed tool.

    Tools are a collection of different scripts to perform different functions
    which aren't native to the ThoughtSpot or advanced functionality for
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
    for tool_name, click_group in ctx.command.commands.items():
        cs_tool = ctx.obj.tools[tool_name]

        if private and cs_tool.privacy == 'private':
            click_group.hidden = False

        if beta and cs_tool.privacy == 'beta':
            click_group.hidden = False

    console.print(ctx.get_help())
    raise typer.Exit(code=0)
