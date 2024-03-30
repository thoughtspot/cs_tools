from __future__ import annotations

from typing import Any
from xml.etree.ElementTree import Element, SubElement
import datetime as dt
import functools as ft
import io

from cs_tools.cli.ux import rich_console
from markdown import Markdown
from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
import cs_tools
import typer


@ft.cache
def _setup_cli() -> typer.Typer:
    """ """
    from cs_tools.cli.commands import (
        config as config_app,
        log as log_app,
        self as self_app,
        tools as tools_app,
    )
    from cs_tools.cli.commands.main import app

    app.add_typer(tools_app.app)
    app.add_typer(config_app.app)
    app.add_typer(self_app.app)
    app.add_typer(log_app.app)
    return app


class CSToolsScreenshotProcesser(BlockProcessor):
    """CSToolsScreenshot block processors."""

    BASE_FILEPATH = cs_tools.utils.get_package_directory("cs_tools").parent / "docs" / "terminal-screenshots"
    BLOCK_IDENTITY = "~cs~tools"
    CLASS_NAME = "screenshotter"

    def _path_safe_command(self, command: Any) -> str:
        """Clean the command to make it pathsafe, for saving SVG to disk."""
        if isinstance(command, list):
            command = " ".join(command)

        assert isinstance(command, str)
        return command.replace(" ", "_").replace("-", "_").replace("://", "_").replace(".", "_")

    def make_svg_screenshot(self, command: list[str]) -> None:
        """Save a screenshot for a given command."""
        if (fp := self.BASE_FILEPATH.joinpath(f"{self._path_safe_command(command)}.svg")).exists():
            now = dt.datetime.now(tz=dt.timezone.utc)
            last_file_audit = dt.datetime.fromtimestamp(fp.stat().st_mtime, tz=dt.timezone.utc)  # type: ignore

            if (now - last_file_audit) <= dt.timedelta(minutes=5):
                return

        cli = _setup_cli()

        # set our Console up for screenshots
        rich_console.width = 135
        rich_console.record = True
        rich_console.file = io.StringIO()

        # call the command in CS Tools
        cli(args=command[1:], prog_name="cs_tools", standalone_mode=False)

        # save to disk
        rich_console.save_svg(fp.as_posix(), title=" ".join(command))

    #
    #
    #

    def test(self, parent: Element, block: str) -> bool:  # noqa: ARG002
        """Determine if a Markdown block of test matches, and if we should write."""
        return block.startswith(self.BLOCK_IDENTITY)

    def run(self, parent: Element, blocks: list[str]) -> bool:
        """Modify the blocks passed in this text blob."""
        for idx, block in enumerate(blocks[:]):
            # Process the block that matches our CS TOOLS tag
            if block.startswith(self.BLOCK_IDENTITY):
                # Pull off the relative path
                _, relative_to_base, *cs_tools_command = block.split(" ")
                pathsafe_command = self._path_safe_command(cs_tools_command)

                # Pop off the tag itself.
                blocks.pop(idx)

                # Create our Screenshot
                self.make_svg_screenshot(cs_tools_command)

                # Add to the parent
                svg = SubElement(
                    parent,
                    f"object class={self.CLASS_NAME} data='{relative_to_base}/terminal-screenshots/{pathsafe_command}.svg'",  # noqa: E501
                )

                # This is recursive, hence why it looks weird (assigning new parent as this child element)
                self.parser.parseBlocks(parent=svg, blocks=[])

                # Continue processing
                return True

        # Stop processing
        return False


class CSToolsScreenshotExtension(Extension):
    """Add CSToolsScreenshot extension."""

    def extendMarkdown(self, md: Markdown) -> None:
        """Add CSToolsScreenshot to Markdown instance."""
        MAGIC_NUMBER = 100  # no idea, it's supposed to be a priority ???

        screenshotter = CSToolsScreenshotProcesser(md.parser)
        screenshotter.BASE_FILEPATH.mkdir(exist_ok=True)

        md.registerExtension(self)
        md.parser.blockprocessors.register(screenshotter, "cs_tools_screenshot", MAGIC_NUMBER)


def makeExtension(**kwargs) -> CSToolsScreenshotExtension:
    """Return extension."""
    return CSToolsScreenshotExtension(**kwargs)
