import pathlib

import awesomeversion
import cs_tools

TEST_DATA_DIRECTORY = pathlib.Path(__file__).parent / ".data"
CST_AVERSION = awesomeversion.AwesomeVersion(cs_tools.__version__)

CST_CONFIG_LATEST = TEST_DATA_DIRECTORY / f"ts-config_version_{CST_AVERSION.major}_{CST_AVERSION.minor}_x.toml"
CST_CONFIG_N_MINUS_1 = TEST_DATA_DIRECTORY / f"ts-config_version_{CST_AVERSION.major}_{CST_AVERSION.section(1) - 1}_x.toml"
CST_CONFIG_DOT_ENV = TEST_DATA_DIRECTORY / ".env"
