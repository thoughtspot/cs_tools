from __future__ import annotations

from typing import Optional
import logging
import shutil

import typer

from cs_tools.cli import custom_types
from cs_tools.settings import (
    CSToolsConfig as _CSToolsConfig,
    _meta_config as meta,
)
from cs_tools.thoughtspot import ThoughtSpot as _ThoughtSpot

_LOG = logging.getLogger(__name__)


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

    config: str = _OPT_CONFIG
    temp_dir: custom_types.Directory = _OPT_TEMP_DIR
    verbose: bool = _OPT_VERBOSE

    def __init__(self, auto_login=True):
        self.ts_config: Optional[_CSToolsConfig] = None
        self.ts: Optional[_ThoughtSpot] = None
        self.auto_login = auto_login

    def __with_user_ctx__(self, ctx: typer.Context, *a, name: str, **kw) -> None:
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
        assert self.ts_config is not None, "The ThoughtSpot dependency has not been initialized yet."

        # CLEAN UP THE TEMPORARY DIRECTORY.
        for path in self.ts_config.temp_dir.iterdir():
            try:
                path.unlink(missing_ok=True) if path.is_file() else shutil.rmtree(path, ignore_errors=True)
            except PermissionError:
                _LOG.warning(f"{path} appears to be in use and can't be cleaned up.. do you have it open somewhere?")

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass
