from __future__ import annotations

import pathlib

from cs_tools import utils
import cs_tools


def test_get_package_directory():
    assert utils.get_package_directory("cs_tools") == pathlib.Path(cs_tools.__file__).parent
