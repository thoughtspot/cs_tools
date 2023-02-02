"""
This file contains the methods to execute the 'scriptability create-mapping' command.
"""
import pathlib

from cs_tools.errors import CSToolsError
from cs_tools.cli.ux import rich_console
from cs_tools.cli.ux import CSToolsArgument as Arg

from ._version import __version__


def create_mapping(
    guid_file: pathlib.Path = Arg(
        ...,
        help="Path to the new mapping file to be created.  Existing files will not be overwritten.",
        metavar="FILE",
        dir_okay=False,
        resolve_path=True,
    ),
):
    """
    Create a new, empty mapping file.
    """
    if create_guid_file_if_not_exists(guid_file):
        rich_console.log(f"[b yellow]File {guid_file} already exists.  Not creating a new one.[/]")
    else:
        rich_console.log(f"[b green]Created {guid_file}.[/]")


def create_guid_file_if_not_exists(guid_file: pathlib.Path) -> bool:
    """
    Creates a GUID file with a standard header if one doesn't exist.
    """
    if not guid_file.exists():
        mapping_header = (
            "# Automatically generated from cstools scriptability.\n"
            'name="generated mapping file"\n'
            'source="Source ThoughtSpot"\n'
            'destination="Destination ThoughtSpot"\n'
            'description=""\n'
            f'version="{__version__}"\n'
            "\n"
            "[mappings]\n"
        )
        try:
            with guid_file.open(mode="w") as f:
                f.write(mapping_header)
        except OSError as e:
            raise CSToolsError(
                error=f"Unable to open file {guid_file}",
                reason=f"Error: {e}",
                mitigation="Verify the file exists and can be read.",
            )

        return False

    return True  # exists already
