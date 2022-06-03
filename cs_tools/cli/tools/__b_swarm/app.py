from typing import TYPE_CHECKING
import logging

from locust.stats import stats_printer, stats_history
from locust.env import Environment
from typer import Argument as A_, Option as O_
import gevent
import typer

from cs_tools.cli.tools import setup_thoughtspot, teardown_thoughtspot
from cs_tools.cli import (
    depends,
    CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT,
    console, CSToolsGroup, CSToolsCommand
)

from .strategies import AnswerUser

if TYPE_CHECKING:
    from typing import List
    from cs_tools.thoughtspot import ThoughtSpot


log = logging.getLogger(__name__)
app = typer.Typer(
    help="""
    Simulate a number of tests against your ThoughtSpot cluster.

    [b][yellow]USE AT YOUR OWN RISK![/][/b][cyan] This tool is currently in beta.[/]
    """,
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
@depends(
    'thoughtspot',
    setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
)
def every(
    ctx: typer.Context,
    total_users: int = A_(..., help='number of users to simulate'),
    content_type: str = O_(None, help='either answer, or liveboard'),
    tag: str = O_(None, help='name of the tag to filter by'),
):
    """
    """
    SPAWN_RATE = 5
    ts = ctx.obj.thoughtspot

    if content_type == 'answer':
        strategy = [AnswerUser]
    # if content_type == 'liveboard':
    #     strategy = [LiveboardUser]

    env = Environment(user_classes=strategy)
    env.thoughtspot = ts
    env.create_local_runner()

    # start a WebUI instance
    env.create_web_ui("127.0.0.1", 8089)

    # start a greenlet that periodically outputs the current stats
    gevent.spawn(stats_printer(env.stats))

    # start a greenlet that save current stats to history
    gevent.spawn(stats_history, env.runner)

    # start the test
    env.runner.start(total_users, spawn_rate=min(total_users, SPAWN_RATE))

    # in 60 seconds stop the runner
    gevent.spawn_later(60, lambda: env.runner.quit())

    # wait for the greenlets
    env.runner.greenlet.join()

    # stop the web server for good measures
    env.web_ui.stop()
