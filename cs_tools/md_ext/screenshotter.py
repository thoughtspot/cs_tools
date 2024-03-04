from __future__ import annotations

from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element, SubElement
import datetime as dt
import functools as ft
import io

from cs_tools.cli.main import _setup_tools, app
from cs_tools.cli.ux import rich_console
from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
import cs_tools

if TYPE_CHECKING:
    from markdown import Markdown
    import typer


@ft.cache
def _setup_cli() -> typer.Typer:
    """ """
    from cs_tools.cli import _config, _log, _self, _tools

    _setup_tools(_tools.app, ctx_settings=app.info.context_settings)
    app.add_typer(_tools.app)
    app.add_typer(_config.app)
    app.add_typer(_self.app)
    app.add_typer(_log.app)
    return app


class CSToolsScreenshotProcesser(BlockProcessor):
    """CSToolsScreenshot block processors."""

    BASE_FILEPATH = cs_tools.utils.get_package_dir("cs_tools") / "docs" / "terminal-screenshots"
    BLOCK_IDENTITY = "~cs~tools"
    CLASS_NAME = "screenshotter"

    def _path_safe_command(self, command: list[str]) -> str:
        """ """
        if isinstance(command, list):
            command = " ".join(command)

        return command.replace(" ", "_").replace("-", "_").replace("://", "_").replace(".", "_")

    def make_svg_screenshot(self, command: list[str]) -> None:
        """Save a screenshot for a given command."""
        file = self.BASE_FILEPATH.joinpath(f"{self._path_safe_command(command)}.svg")
        now = dt.datetime.now(tz=dt.timezone.utc)
        last_file_audit = dt.datetime.fromtimestamp(file.stat().st_mtime, tz=dt.timezone.utc)

        if file.exists() and (now - last_file_audit) <= dt.timedelta(minutes=5):
            return

        cli = _setup_cli()

        # set our Console up for screenshots
        rich_console.width = 135
        rich_console.record = True
        rich_console.file = io.StringIO()

        # call the command in CS Tools
        cli(args=command[1:], prog_name="cs_tools", standalone_mode=False)

        # save to disk
        rich_console.save_svg(f"{self.BASE_FILEPATH}/{self._path_safe_command(command)}.svg", title=" ".join(command))

    #
    #
    #

    def test(self, parent: Element, block: str) -> bool:  # noqa: ARG002
        """Determine if a Markdown block of test matches, and if we should write."""
        return block.startswith(self.BLOCK_IDENTITY)

    def run(self, parent: Element, blocks: list[str]) -> None:
        """Modify the blocks passed in this text blob."""
        for idx, block in enumerate(blocks[:]):
            # Process the block that matches our CS TOOLS tag
            if block.startswith(self.BLOCK_IDENTITY):
                # Pull off the relative path
                _, relative_to_base, *cs_tools_command = block.split(" ")

                # Pop off the tag itself.
                blocks.pop(idx)

                # Create our Screenshot
                self.make_svg_screenshot(cs_tools_command)

                # Add to the parent
                pathsafe_command = self._path_safe_command(cs_tools_command)
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
