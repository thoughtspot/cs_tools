# DEV NOTE:
#
# Future enhancements:
#   - ability to manipulate objects, such as renaming references to worksheets and tables, token replacement, etc.
#   - add support for tables and connections
#   - add support for importing .zip files
#
from __future__ import annotations
from typing import Optional, List
import logging
import pathlib

import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import MultipleChoiceType
from thoughtspot_tml import Connection
from cs_tools.cli.ux import CSToolsArgument as Arg
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import CSToolsApp
from cs_tools.cli.ux import rich_console
from cs_tools.types import GUID, TMLImportPolicy

from ._compare import compare
from ._import import to_import
from ._export import export
from . import layout

log = logging.getLogger(__name__)
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


@app.command(dependencies=[thoughtspot], hidden=True)
def connection_rationalize(
    ctx: typer.Context,
    connection_guid: GUID = Opt(..., help="connection GUID"),
    # directory: pathlib.Path = Opt(..., help="directory to save data to"),
):
    ts = ctx.obj.thoughtspot

    r = ts.api.connection_export(guid=connection_guid)
    tml = Connection.loads(r.text)
    tml.guid = connection_guid

    external_tables = [
        {
            "databaseName": table.external_table.db_name,
            "schemaName": table.external_table.schema_name,
            "tableName": table.external_table.table_name
        }
        for table in tml.connection.table
    ]

    r = ts.api.connection_fetch_connection(guid=tml.guid)
    d = r.json()
    i = tml.to_rest_api_v1_metadata()

    r = ts.api.connection_fetch_live_columns(
            guid=tml.guid,
            tables=external_tables,
            config=i["configuration"],
            authentication_type=d["authenticationType"]
        )

    if r.is_error:
        log.error(f"encountered an error fetching columns from [b blue]{tml.name}[/]\n{r.json()}")
        raise typer.Exit(1)

    need_to_fix = []
    unsynced_columns = 0

    for fully_qualified_tablename, columns in r.json().items():
        n = 0
 
        for column in columns:
            if column["selected"] and not column["isLinkedActive"]:
                n += 1

        if n > 0:
            unsynced_columns += n
            database, schema, table = fully_qualified_tablename.split(".")
            need_to_fix.append(
                {
                    "database": database,
                    "schema": schema,
                    "table": table,
                    "unsynced_columns": n,
                    "is_whole_table_unsynced": n == len(columns),
                }
            )

    if need_to_fix:
        log.warning(
            f"[b yellow]{unsynced_columns} columns across {len(need_to_fix)} tables are out of sync in "
            f"[b blue]{tml.name}"
        )
        table = layout.build_table()
        [table.renderable.add_row(*map(str, row.values())) for row in need_to_fix]
        rich_console.print(table)


@app.command(dependencies=[thoughtspot], name="export")
def scriptability_export(
    ctx: typer.Context,
    directory: pathlib.Path = Arg(
        ..., help="directory to save TML to", file_okay=False, resolve_path=True, exists=True
    ),
    tags: str = Opt(
        None,
        custom_type=MultipleChoiceType(),
        help="objects marked with tags to export, comma separated",
    ),
    guids: str = Opt(
        None,
        custom_type=MultipleChoiceType(),
        help="specific objects to export, comma separated",
    ),
    author: str = Opt(None, help="objects authored by this username to export"),
    pattern: str = Opt(None, help=r"object names which meet a pattern, follows SQL LIKE operator (% as a wildcard)"),
    include_types: str = Opt(
        None,
        custom_type=MultipleChoiceType(),
        help="list of types to export: answer, liveboard, view, sqlview, table, connection",
    ),
    exclude_types: str = Opt(
        None,
        custom_type=MultipleChoiceType(),
        help="list of types to exclude (overrides include): answer, liveboard, view, sqlview, table, connection",
    ),
    export_associated: bool = Opt(
        False, 
        "--export-associated",
        help="if specified, also export related content"
    ),
    org: str = Opt(None, help="name or ID of the org to export from", hidden=True),
):
    """
    Exports TML from ThoughtSpot.

    There are different parameters that can impact content to download. At least one
    needs to be specified.

    - GUIDs: only content with the specific GUIDs will be downloaded.
    - filters, e.g tags, author, pattern, include_types, exclude_types.

    If you specify GUIDs then you can't use any filters.

    Filters are applied in AND fashion - only items that match all filters will be
    exported. For example, if you export for the "finance" tag and author "user123",
    then only content owned by that user with the "finance" tag will be exported.
    """
    export(
        ts=ctx.obj.thoughtspot,
        path=directory,
        tags=tags,
        guids=guids,
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
    directory: pathlib.Path = Arg(
        ..., help="directory to load TML from", file_okay=False, resolve_path=True
    ),
    import_policy: TMLImportPolicy = Opt(TMLImportPolicy.validate, help="The import policy type"),
    force_create: bool = Opt(False, "--force-create", help="will force a new object to be created"),
    guid_file: Optional[pathlib.Path] = Opt(
        None,
        help="existing or new mapping file to map GUIDs from source instance to target instance",
        dir_okay=False,
        resolve_path=True,
    ),
    from_env: str = Opt(None, help="the source environment name importing from", rich_help_panel="GUID Mapping Options"),
    to_env: str = Opt(None, help="the target environment name importing to", rich_help_panel="GUID Mapping Options"),
    tags: List[str] = Opt([], help="one or more tags to add to the imported content"),
    share_with: List[str] = Opt([], help="one or more groups to share the uploaded content with"),
    org: str = Opt(None, help="name of org to import to"),
):
    """
    Import TML from a file or directory into ThoughtSpot.

    \b
    cs_tools dependends on thoughtspot_tml. The GUID file is produced from
    thoughtspot_tml and requires a specific format. For further information on the
    GUID File, see

       https://github.com/thoughtspot/thoughtspot_tml/tree/v2_0_release#environmentguidmapper
    """
    to_import(
        ctx=ctx,
        path=directory,
        import_policy=import_policy,
        force_create=force_create,
        guid_file=guid_file,
        from_env=from_env,
        to_env=to_env,
        tags=tags,
        share_with=share_with,
        org=org,
    )


@app.command(name="compare")
def scriptability_compare(
    file1: pathlib.Path = Arg(
        ..., help="full path to the first TML file to compare", dir_okay=False, resolve_path=True
    ),
    file2: pathlib.Path = Arg(
        ..., help="full path to the second TML file to compare", dir_okay=False, resolve_path=True
    ),
):
    """
    Compares two TML files for differences.
    """
    compare(file1=file1, file2=file2)
