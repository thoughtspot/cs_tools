from __future__ import annotations

import pathlib

import pytest

from tests import const


@pytest.fixture(scope="session")
def cleaned_generated_test_data_dir() -> pathlib.Path:
    generated = const.TEST_DATA_DIRECTORY.joinpath("generated")

    # CREATE
    generated.mkdir(parents=True, exist_ok=True)

    # CLEAN
    [f.unlink() for f in generated.iterdir()]

    return generated
