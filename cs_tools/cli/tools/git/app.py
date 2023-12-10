# DEV NOTE:
#
# Future enhancements:
#   - add more flexibility and workflows
#
from __future__ import annotations

import logging

from cs_tools.cli.ux import CSToolsApp

from .branches import app as branchesApp
from .config import app as configApp

log = logging.getLogger(__name__)

app = CSToolsApp(
    help="""
    Allows you to use the vsc/git API endpoints in a developer friendly way.

    See https://developers.thoughtspot.com/docs/git-integration for more details.
    """,
    options_metavar="[--version, --help]",
)
app.add_typer(configApp, name="config", help="Commands managing the git configurations.")
app.add_typer(branchesApp, name="branches", help="Commands for working with branches and commits.")
