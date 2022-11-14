import typer

from cs_tools.settings import _meta_config
from cs_tools.cli.ux import console, CSToolsGroup
from cs_tools.const import DOCS_BASE_URL, GH_ISSUES, GDRIVE_FORM

meta = _meta_config()
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
    epilog=(
        f":books: [cyan][link={DOCS_BASE_URL}/cs-tools/overview/]Documentation[/] "
        f"🛟 [link={GH_ISSUES}]Get Help[/] "
        f":memo: [link={GDRIVE_FORM}]Feedback[/][/] "
        + (f":computer_disk: [green]{meta.default_config_name}[/] (default)" if meta.default_config_name is not None else "")
    )
)
