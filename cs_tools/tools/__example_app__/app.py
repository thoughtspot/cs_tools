# DEV NOTE:
#   This file should app's version identifier. We use semantic versioning.
#
#   Further reading:
#   https://semver.org/
#

from typer import Argument as A_, Option as O_  # noqa
import typer


app = typer.Typer(
    help="""
    One-liner describing the tool.

    Further explanation explaining the tool's usage or purpose.

    If more ideas need to be conveyed, use separate paragraphs.

    For further information on <idea expressed in doc>, please refer to:
      https://docs.thoughtspot.com/path/to/documenation-link.html
    """
)
