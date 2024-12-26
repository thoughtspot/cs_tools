from __future__ import annotations

import logging

import typer

from cs_tools import utils
from cs_tools.cli import custom_types
from cs_tools.settings import (
    CSToolsConfig as _CSToolsConfig,
    _meta_config as meta,
)
from cs_tools.thoughtspot import ThoughtSpot as _ThoughtSpot

log = logging.getLogger(__name__)


_HELP_PANEL_GROUP = "[ThoughtSpot Config Overrides]"

_OPT_CONFIG = typer.Option(
    ... if meta.default_config_name is None else meta.default_config_name,
    "--config",
    help="Name of your ThoughtSpot config file.",
    metavar="NAME",
    rich_help_panel=_HELP_PANEL_GROUP,
)

_OPT_TEMP_DIR: custom_types.Directory = typer.Option(
    None,
    "--temp-dir",
    help="Path to save file temporary files to.",
    show_default=False,
    rich_help_panel=_HELP_PANEL_GROUP,
)

_OPT_VERBOSE: bool = typer.Option(
    None,
    "--verbose",
    help="Write log files with more detail.",
    show_default=False,
    rich_help_panel=_HELP_PANEL_GROUP,
)


class ThoughtSpot:
    """Injects the cs_tools.thoughtspot.ThoughtSpot object into the CLI context."""

    config: str | None = _OPT_CONFIG
    temp_dir: custom_types.Directory = _OPT_TEMP_DIR
    verbose: bool = _OPT_VERBOSE

    def __init__(self, auto_login=True):
        self.ts_config: _CSToolsConfig | None = None
        self.ts: _ThoughtSpot | None = None
        self.auto_login = auto_login

    def __with_user_setup__(self, ctx: typer.Context, *a, name: str, **kw) -> None:
        config_overides = {}

        if ctx.params["temp_dir"] is not None:
            config_overides["temp_dir"] = ctx.params["temp_dir"]

        if ctx.params["verbose"] is not None:
            config_overides["verbose"] = ctx.params["verbose"]

        self.ts_config = _CSToolsConfig.from_name(ctx.params["config"], automigrate=True, **config_overides)
        self.ts = _ThoughtSpot(self.ts_config, auto_login=self.auto_login)

        # Make `ThoughtSpot` available as on the ctx.obj namespace.
        setattr(ctx.obj, name, self.ts)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass
