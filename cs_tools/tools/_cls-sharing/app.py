from typer import Argument as A_, Option as O_  # noqa
import uvicorn
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.settings import TSConfig
from cs_tools.api import ThoughtSpot

from .web_app import _scoped


app = typer.Typer(
    help="""
    Scalably manage your table- and column-level security right in the browser.

    [b][yellow]USE AT YOUR OWN RISK![/b] This tool uses private API calls which
    could change on any version update and break the tool.[/]

    Setting up Column Level Security (especially on larger tables) can be time-consuming
    when done directly in the ThoughtSpot user interface. The web interface provided by
    this tool will allow you to quickly understand the current security settings for a
    given table across all columns, and as many groups as are in your platform. You may
    then set the appropriate security settings for those group-table combinations.
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def run(
    **frontend_kw
):
    """
    Start the built-in webserver which runs the security management interface.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as api:
        _scoped['api'] = api

        console.print(
            'starting webserver...'
            '\nplease visit http://cs_tools.localho.st:5000/ in your browser'
        )

        uvicorn.run(
            'cs_tools.tools._cls-sharing.web_app:web_app',
            host='0.0.0.0',
            port=5000,
            # log_config=None
        )
