from ward import fixture

from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig


@fixture(scope='global')
def thoughtspot():
    cfg = TSConfig.from_toml('tests/_test_config.toml')

    with ThoughtSpot(config=cfg) as ts:
        yield ts
