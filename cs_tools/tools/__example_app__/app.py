# DEV NOTE:
#

from typer import Argument as A_, Option as O_  # noqa
import typer


app = typer.Typer(
    help="""
    One-liner describing the tool.

    Further explanation explaining the tool's usage or purpose. This can
    be as long as is necessary, but be mindful of much content you type
    here as the full text will display in the console when the user
    types...

      cs_tools tools my-cool-app --help

    If more ideas need to be conveyed, use separate paragraphs. Content
    will be wrapped to the console spec (default: 125 characters) unless
    you use a control character.

    Many tools augment a ThoughtSpot service. If they do, a relevant
    documentation link should be provided.

    \b
    For further information on <idea expressed in doc>, please refer to:
      https://docs.thoughtspot.com/path/to/documenation-link.html

    \f
    DEV NOTE:

      Two control characters are offered in order to help with
      docstrings in typer App helptext and command helptext
      (docstrings).

      \b - Preserve Whitespace / formatting.
      \f - EOF, don't include anything after this character in helptext.
    """
)
