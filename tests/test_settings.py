from __future__ import annotations

from typing import TYPE_CHECKING

from cs_tools.settings import CSToolsConfig
import pytest
import toml

from . import const

if TYPE_CHECKING:
    import pathlib


def test_migrate_from_n_minus_one_config():
    """
    We should not be afraid to make backwards incompatible changes to configuration
    files between releases since the CLI handles CRUD operations on these files.
    """
    conf = CSToolsConfig.from_toml(path=const.CST_CONFIG_N_MINUS_1, automigrate=False)
    data = conf.model_dump()

    assert const.CST_CONFIG_N_MINUS_1.read_text() != toml.dumps(data)


@pytest.mark.parametrize(
    "conf_fp",
    [
        pytest.param(const.CST_CONFIG_LATEST, id="CONF_LATEST"),
        pytest.param(const.CST_CONFIG_N_MINUS_1, id="CONF_N_MINUS_1"),
    ],
)
def test_load_from_toml(conf_fp: pathlib.Path):
    """
    CSToolsConfig.from_toml() is the main serialization method.
    """
    conf = CSToolsConfig.from_toml(path=conf_fp, automigrate=False)
    data = conf.model_dump()

    assert conf == CSToolsConfig(**data)
