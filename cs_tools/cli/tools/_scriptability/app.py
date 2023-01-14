# DEV NOTE:
#
# Future enhancements:
#   - ability to manipulate objects, such as renaming references to worksheets and tables, token replacement, etc.
#   - add support for tables and connections
#   - add support for importing .zip files
#
from typing import Optional, List
import pathlib

from typer import Argument as A_
from typer import Option as O_
import typer
import click

from cs_tools.cli.tools.common import teardown_thoughtspot, setup_thoughtspot
from cs_tools.cli.dependency import depends
from cs_tools.cli.options import TEMP_DIR_OPT, VERBOSE_OPT, CONFIG_OPT
from cs_tools.data.enums import TMLImportPolicy
from cs_tools.cli.ux import CSToolsCommand, CSToolsGroup

from ._compare import compare
from ._import import import_
from ._export import export

app = typer.Typer(
    help="""
    Tool for easily migrating TML between instance.

    [b][yellow]USE AT YOUR OWN RISK![/b] This tool uses private API calls which
    could change on any version update and break the tool.[/]

    ThoughtSpot provides the ability to extract object metadata (tables, worksheets, liveboards, etc.) 
    in ThoughtSpot Modeling Language (TML) format, which is a text format based on YAML.  
    These files can then be modified and imported into another (or the same) instance to either create 
    or modify objects.

      cs_tools tools scriptability --help
    
    \f
    """,
    cls=CSToolsGroup,
    options_metavar="[--version, --help]",
)


@app.command(cls=CSToolsCommand, name="export")
@depends(
    "thoughtspot",
    setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
)
def scriptability_export(
    ctx: click.Context,
    path: pathlib.Path = A_(  # may not want to use
        ..., help="full path (directory) to save data set to", metavar="DIR", dir_okay=True, resolve_path=True
    ),
    tags: List[str] = O_([], metavar="TAGS", help="comma separated list of tags to export"),
    export_ids: List[str] = O_(
        [],
        metavar="GUIDS",
        help="comma separated list of GUIDs to export " "that cannot be combined with other filters",
    ),
    author: str = O_(None, metavar="USERNAME", help="username that is the author of the content to download"),
    pattern: str = O_(None, metavar="PATTERN", help="Pattern for name with % as a wildcard"),
    include_types: List[str] = O_(
        [],
        metavar="CONTENTTYPES",
        help="list of types to include: answer, liveboard, view, sqlview, " "table, connection",
    ),
    exclude_types: List[str] = O_(
        [],
        metavar="CONTENTTYPES",
        help="list of types to exclude (overrides include): answer, liveboard, view, " "sqlview, table, connection",
    ),
    export_associated: bool = O_(False, help="if specified, also export related content"),
    set_fqns: bool = O_(False, help="if set, then the content in the TML will have FQNs (GUIDs) added."),
    org: str = O_(None, help="Name of org to export from.  The user must have access to that org."),
):
    export(
        ctx=ctx,
        path=path,
        tags=tags,
        export_ids=export_ids,
        author=author,
        pattern=pattern,
        include_types=include_types,
        exclude_types=exclude_types,
        export_associated=export_associated,
        set_fqns=set_fqns,
        org=org,
    )


@app.command(cls=CSToolsCommand, name="import")
@depends(
    "thoughtspot",
    setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
)
def scriptability_import(
    ctx: click.Context,
    path: pathlib.Path = A_(
        ...,
        help="full path to the TML file or directory to import.",
        metavar="FILE_OR_DIR",
        dir_okay=True,
        resolve_path=True,
    ),
    import_policy: TMLImportPolicy = O_(TMLImportPolicy.validate_only.value, help="The import policy type"),
    force_create: bool = O_(False, help="If true, will force a new object to be created."),
    guid_file: Optional[pathlib.Path] = O_(
        None,
        help="Existing or new mapping file to map GUIDs from source instance to target instance.",
        metavar="FILE_OR_DIR",
        dir_okay=False,
        resolve_path=True,
    ),
    from_env: str = O_(None, help="The environment name importing from, for GUID mapping."),
    to_env: str = O_(None, help="The environment name importing to, for GUID mapping."),
    tags: List[str] = O_([], metavar="TAGS", help="One or more tags to add to the imported content."),
    share_with: List[str] = O_([], metavar="GROUPS", help="One or more groups to share the uploaded content with."),
    tml_logs: Optional[pathlib.Path] = O_(
        None,
        help="full path to the directory to log sent TML.  TML can change during load.",
        metavar="DIR",
        dir_okay=True,
        resolve_path=True,
    ),
    org: str = O_(None, help="Name of org to import to.  The user must have access to that org."),
):
    import_(
        ctx=ctx,
        path=path,
        import_policy=import_policy,
        force_create=force_create,
        guid_file=guid_file,
        from_env=from_env,
        to_env=to_env,
        tags=tags,
        share_with=share_with,
        tml_logs=tml_logs,
        org=org,
    )


@app.command(name="compare", cls=CSToolsCommand)
def scriptability_compare(
    file1: pathlib.Path = A_(
        ..., help="full path to the first TML file to compare.", metavar="FILE1", dir_okay=False, resolve_path=True
    ),
    file2: pathlib.Path = A_(
        ..., help="full path to the second TML file to compare.", metavar="FILE2", dir_okay=False, resolve_path=True
    ),
):
    compare(file1=file1, file2=file2)
