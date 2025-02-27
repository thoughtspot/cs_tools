from __future__ import annotations

from cs_tools.cli.ux import AsyncTyper

from .branches import app as branches_app
from .config import app as config_app

app = AsyncTyper(help="Allows you to use the vsc/git API endpoints in a developer friendly way.")
app.add_typer(config_app)
app.add_typer(branches_app)
