# ruff: noqa: RUF012
from __future__ import annotations

import logging

from textual.app import App

from cs_tools import _types
from cs_tools.api.client import RESTAPIClient
from cs_tools.cli.tools.bulk_sharing import screens

log = logging.getLogger(__name__)


class ThoughtSpotSecurityApp(App):
    """Manage your object-level and column-level security."""

    MODES = {
        "splash": screens.SecuritySplash,
        "home": screens.SecurityHome,
        "security": screens.SecurityConfig,
    }

    def __init__(self, http: RESTAPIClient, ts_version: str):
        super().__init__()
        self.http = http
        self.compat_ts_version = ts_version
        self.active_table: types.APIResult | None = None
        self.active_groups: list[types.APIResult] | None = None
        self.active_table_security: list[types.APIResult] | None = None

    def on_mount(self) -> None:
        self.switch_mode("splash")


if __name__ == "__main__":
    # ================================================================//
    #
    # DO NOT EDIT!!! THIS IS NEEDED FOR app.py --mode web TO WORK.
    #
    import argparse

    from cs_tools.settings import CSToolsConfig
    from cs_tools.thoughtspot import ThoughtSpot

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Configuration file identifier", default=None)
    option = parser.parse_args()

    cfg = CSToolsConfig.from_name(name=option.config)
    tse = ThoughtSpot(config=cfg, auto_login=True)
    #
    # ================================================================//
    app = ThoughtSpotSecurityApp(http=tse.api, ts_version=tse.session_context.thoughtspot.version)
    app.run()
