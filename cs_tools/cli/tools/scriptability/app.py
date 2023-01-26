# DEV NOTE:
#
# Future enhancements:
#   - ability to manipulate objects, such as renaming references to worksheets and tables, token replacement, etc.
#   - add support for tables and connections
#   - add support for importing .zip files
#
from typing import Optional, List
import pathlib

import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.ux import CSToolsArgument as Arg
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import CSToolsApp
from cs_tools.types import TMLImportPolicy

from ._compare import compare
from ._import import to_import
from ._export import export

app = CSToolsApp(
    help="""
    Tool for easily migrating TML between instance.

    ThoughtSpot provides the ability to extract object metadata (tables, worksheets, liveboards, etc.) 
    in ThoughtSpot Modeling Language (TML) format, which is a text format based on YAML.  
    These files can then be modified and imported into another (or the same) instance to either create 
    or modify objects.
    """,
    options_metavar="[--version, --help]",
)


@app.command(dependencies=[thoughtspot], name="export")
def scriptability_export(
    ctx: typer.Context,
    path: pathlib.Path = Arg(  # may not want to use
        ..., help="full path (directory) to save data set to", metavar="DIR", dir_okay=True, resolve_path=True
    ),
    tags: List[str] = Opt([], metavar="TAGS", help="comma separated list of tags to export"),
    export_ids: List[str] = Opt(
        [],
        metavar="GUIDS",
        help="comma separated list of GUIDs to export " "that cannot be combined with other filters",
    ),
    author: str = Opt(None, metavar="USERNAME", help="username that is the author of the content to download"),
    pattern: str = Opt(None, metavar="PATTERN", help="Pattern for name with % as a wildcard"),
    include_types: List[str] = Opt(
        [],
        metavar="CONTENTTYPES",
        help="list of types to include: answer, liveboard, view, sqlview, " "table, connection",
    ),
    exclude_types: List[str] = Opt(
        [],
        metavar="CONTENTTYPES",
        help="list of types to exclude (overrides include): answer, liveboard, view, " "sqlview, table, connection",
    ),
    export_associated: bool = Opt(False, help="if specified, also export related content"),
    org: str = Opt(None, help="Name of org to export from.  The user must have access to that org."),
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
        org=org,
    )


@app.command(dependencies=[thoughtspot], name="import")
def scriptability_import(
    ctx: typer.Context,
    path: pathlib.Path = Arg(
        ...,
        help="full path to the TML file or directory to import.",
        metavar="FILE_OR_DIR",
        dir_okay=True,
        resolve_path=True,
    ),
    import_policy: TMLImportPolicy = Opt(TMLImportPolicy.validate, help="The import policy type"),
    force_create: bool = Opt(False, help="If true, will force a new object to be created."),
    guid_file: Optional[pathlib.Path] = Opt(
        None,
        help="Existing or new mapping file to map GUIDs from source instance to target instance.",
        metavar="FILE_OR_DIR",
        dir_okay=False,
        resolve_path=True,
    ),
    from_env: str = Opt(None, help="The environment name importing from, for GUID mapping."),
    to_env: str = Opt(None, help="The environment name importing to, for GUID mapping."),
    tags: List[str] = Opt([], metavar="TAGS", help="One or more tags to add to the imported content."),
    share_with: List[str] = Opt([], metavar="GROUPS", help="One or more groups to share the uploaded content with."),
    tml_logs: Optional[pathlib.Path] = Opt(
        None,
        help="full path to the directory to log sent TML.  TML can change during load.",
        metavar="DIR",
        dir_okay=True,
        resolve_path=True,
    ),
    org: str = Opt(None, help="Name of org to import to.  The user must have access to that org."),
):
    to_import(
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


@app.command(name="compare")
def scriptability_compare(
    file1: pathlib.Path = Arg(
        ..., help="full path to the first TML file to compare.", metavar="FILE1", dir_okay=False, resolve_path=True
    ),
    file2: pathlib.Path = Arg(
        ..., help="full path to the second TML file to compare.", metavar="FILE2", dir_okay=False, resolve_path=True
    ),
):
    compare(file1=file1, file2=file2)
