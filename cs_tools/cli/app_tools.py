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
    invoke_without_command=True,
)
