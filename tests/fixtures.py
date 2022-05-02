import os

from typer.testing import CliRunner
from ward import fixture

from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.cli._loader import _gather_tools
from cs_tools.settings import TSConfig

from cs_tools.cli.app_config import app as cfg_app
from cs_tools.cli.app_log import app as log_app
from cs_tools.cli.tools import app as tools_app
from cs_tools.cli.main import app as app_


@fixture(scope='global')
def thoughtspot():
    cfg = TSConfig.from_command(config=os.environ.get('WARD_TS_CONFIG_NAME'))

    with ThoughtSpot(config=cfg) as ts:
        yield ts


@fixture(scope='global')
def app_runner():
    return CliRunner()


@fixture(scope='global')
def app():
    _gather_tools(tools_app)
    app_.add_typer(tools_app)
    app_.add_typer(cfg_app)
    app_.add_typer(log_app)
    yield app_
