import logging

from typer import Argument as A_, Option as O_
import typer

from cs_tools.cli.ux import CSToolsApp


log = logging.getLogger(__name__)
app = CSToolsApp(help="""Simulate a number of tests against your ThoughtSpot cluster.""")


@app.command()
def foo():
    ...


@app.command()
def bar():
    ...
