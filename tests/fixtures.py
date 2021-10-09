from typer.testing import CliRunner
from ward import fixture

from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig
from cs_tools.cli import _gather_tools, app as app_, tools_app, cfg_app, log_app


@fixture(scope='global')
def thoughtspot():
    # cfg = TSConfig.from_toml('tests/_test_config_6-3-1.toml')
    cfg = TSConfig.from_toml('tests/_test_config_cloud.toml')

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
