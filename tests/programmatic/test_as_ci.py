from __future__ import annotations

import logging
import os

from cs_tools.settings import CSToolsConfig
from cs_tools.thoughtspot import ThoughtSpot
from tests import const

log = logging.getLogger(__name__)


def test_build_config_from_envvar():
    """
    For running in serverless environments, we should be able to parse
    environment variables.
    """
    data = {
        "name": "dogfood",
        "temp_dir": const.TEST_DATA_DIRECTORY,
        "thoughtspot": {
            "url": "https://dogfood.thoughtspot.cloud",
            "username": "really-fake-service-account",
            "password": "eNorSk3MyanULS4tSC3SLU5NLkot0S0uKcrPS9ctSCwuLs8vSgEA-k4OAw==",
        },
    }

    fake = CSToolsConfig.model_validate(data)

    # Simulate ENVIRONMENT VARS being set.
    os.environ["CS_TOOLS_TEMP_DIR"] = data["temp_dir"].as_posix()
    os.environ["CS_TOOLS_THOUGHTSPOT__URL"] = data["thoughtspot"]["url"]
    os.environ["CS_TOOLS_THOUGHTSPOT__USERNAME"] = data["thoughtspot"]["username"]
    os.environ["CS_TOOLS_THOUGHTSPOT__PASSWORD"] = data["thoughtspot"]["password"]

    conf = CSToolsConfig.from_environment()

    # Unset ENVIRONMENT VARS.
    del os.environ["CS_TOOLS_TEMP_DIR"]
    del os.environ["CS_TOOLS_THOUGHTSPOT__URL"]
    del os.environ["CS_TOOLS_THOUGHTSPOT__USERNAME"]
    del os.environ["CS_TOOLS_THOUGHTSPOT__PASSWORD"]

    # fmt: off
    assert fake.temp_dir == conf.temp_dir == const.TEST_DATA_DIRECTORY
    assert fake.thoughtspot.url == conf.thoughtspot.url == "https://dogfood.thoughtspot.cloud" 
    assert fake.thoughtspot.username == conf.thoughtspot.username == "really-fake-service-account"
    assert fake.thoughtspot.password == conf.thoughtspot.password == "eNorSk3MyanULS4tSC3SLU5NLkot0S0uKcrPS9ctSCwuLs8vSgEA-k4OAw=="  # noqa: E501
    # fmt: on


def test_integration_lib_login():
    """
    For running in serverless environments, we should be able to parse
    environment variables.
    """
    conf = CSToolsConfig.from_environment(dotfile=const.CST_CONFIG_DOT_ENV)

    thoughtspot = ThoughtSpot(config=conf)
    thoughtspot.login()

    assert thoughtspot.session_context is not None
