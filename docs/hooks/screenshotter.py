from __future__ import annotations

from typing import Optional
import functools as ft
import logging
import pathlib
import re
import shutil

from cs_tools import utils
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page
from slugify import slugify

_LOG = logging.getLogger(__name__)

PATH_SAFE_MAX_LENGTH = 256
"""Windows default MAX_PATH is 256. POSIX is configurable, but much longer."""

CS_TOOLS_IDENTITY = "~cs~tools"
RE_BLOCK_IDENTITY = re.compile(
    # MATCH A BLOCK IDENTITY AT THE START OF THE LINE (^), THROUGH THE END OF THE LINE ($).
    #   THE IDENTITY AND THE COMMAND MAY BE OPTIONALLY SEPARATED BY ONE OR MORE SPACES.
    rf"{CS_TOOLS_IDENTITY} +?(?P<command>.*)$",
    flags=re.VERBOSE + re.MULTILINE,
)

SCREENSHOT_CACHE: dict[str, pathlib.Path] = {}
"""Simple cache so we can skip re-generating screenshots during docs builds."""


@ft.cache
def _setup_cs_tools_cli() -> AsyncTyper:
    """Fetch the CS Tools CLI."""
    from cs_tools.cli import _monkey  # noqa: F401
    from cs_tools.cli.commands import (
        config as config_command,
        log as log_command,
        self as self_command,
        tools as tools_command,
    )
    from cs_tools.cli.commands.main import app

    tools_command._discover_tools()

    app.add_typer(tools_command.app)
    app.add_typer(config_command.app)
    app.add_typer(self_command.app)
    app.add_typer(log_command.app)

    return app


def on_page_markdown(markdown: str, page: Page, config: MkDocsConfig, files: Files) -> Optional[str]:
    """
    Called after the page's markdown is loaded from file and can be used to alter the Markdown source text.

    Replace the ~cs~tools placeholder with their screenshot SVG content.

    Further reading:
      https://www.mkdocs.org/dev-guide/plugins/#on_page_markdown
    """
    site_dir = pathlib.Path(config["site_dir"])
    scrn_dir = site_dir / "generated" / "screenshots"

    app = _setup_cs_tools_cli()

    if _REFRESH_SCREENSHOTS_DIRECTORY := (not SCREENSHOT_CACHE):
        shutil.rmtree(scrn_dir, ignore_errors=True)
        scrn_dir.mkdir(parents=True, exist_ok=True)

    for match in RE_BLOCK_IDENTITY.finditer(markdown):
        cs_tools_command = match.group("command").strip()
        svg_name = slugify(
            text=cs_tools_command,
            max_length=PATH_SAFE_MAX_LENGTH - len(scrn_dir.as_posix()),
            separator="__",
            lowercase=True,
            allow_unicode=False,
        )

        try:
            svg_path = SCREENSHOT_CACHE[svg_name]

        except KeyError:
            svg_path = scrn_dir / f"{svg_name}.svg"

            with utils.record_screenshots(RICH_CONSOLE, path=svg_path):
                _ = app(cs_tools_command.split(), prog_name="cs_tools", standalone_mode=False)

            SCREENSHOT_CACHE[svg_name] = svg_path

        # CALCULATE THE RELATIVE PATH TO THE SCREENSHOTS DIRECTORY FROM THE CURRENT PAGE.
        cd = "/".join("." if page.parent is None else ".." for _ in range(page.file.url.count("/")))
        fp = f"{cd}/generated/screenshots/{svg_name}.svg"

        block_identity_command = match.string[match.start() : match.end()]
        screenshot_img_src_tag = f'<img src="{fp}" alt="{block_identity_command}" />'

        markdown = markdown.replace(block_identity_command, screenshot_img_src_tag)

    return markdown
