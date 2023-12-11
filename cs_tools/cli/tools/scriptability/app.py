# DEV NOTE:
#
# Future enhancements:
#   - ability to manipulate objects, such as renaming references to worksheets and tables, token replacement, etc.
#   - add support for tables and connections
#   - add support for importing .zip files
#
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Optional
import logging
import pathlib

from thoughtspot_tml import Connection
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.types import MultipleChoiceType, SyncerProtocolType
from cs_tools.cli.ux import CSToolsApp, rich_console
from cs_tools.types import GUID, TMLImportPolicy

from . import layout
from ._compare import compare
from ._export import export
from ._import import to_import
from ._mapping import app as mappingApp
from .tmlfs import app as tmlfsApp

log = logging.getLogger(__name__)
app = CSToolsApp(
    help="""
    Tool for migrating TML between instance.

    ThoughtSpot provides the ability to extract object metadata (tables, worksheets, liveboards, etc.) 
    in ThoughtSpot Modeling Language (TML) format, which is a text format based on YAML.  
    These files can then be modified and imported into another (or the same) instance to either create 
    or modify objects.
    """,
    options_metavar="[--version, --help]",
)
app.add_typer(tmlfsApp, name="tmlfs", help="Commands for working with the TML file system")
app.add_typer(mappingApp, name="mapping", help="Commands for working with TML GUID mappings")


@dataclass
class MetadataColumn:
    database: str
    schema: str
    table: str
    column: str
    data_type_internal: str
    data_type_external: str
    is_missing_external: bool

    @property
    def fully_qualified_name(self) -> str:
        return f"{self.database}.{self.schema}.{self.table}"

    @property
    def is_out_of_sync(self) -> bool:
        return self.is_missing_external or self.data_type_internal != self.data_type_external

    @property
    def values(self) -> Iterable[str]:
        row = (
            self.database,
            self.schema,
            self.table,
            self.column,
            self.data_type_internal,
            self.data_type_external,
            str(self.is_missing_external),
        )
        return row

    def dict(self) -> dict[str, str]:  # noqa: A003
        row = {
            "database": self.database,
            "schema": self.schema,
            "table": self.table,
            "column": self.column,
            "data_type_internal": self.data_type_internal,
            "data_type_external": self.data_type_external,
            "is_missing_external": str(self.is_missing_external),
        }
        return row


@app.command(dependencies=[thoughtspot])
def connection_check(
    ctx: typer.Context,
    org: str = typer.Option(None, help="organization to use"),
    connection_guid: GUID = typer.Option(..., help="connection GUID"),
    syncer: DSyncer = typer.Option(
        None,
        custom_type=SyncerProtocolType(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
):
    """
    Check a Connection's metadata against the external data platform.
    """
    ts = ctx.obj.thoughtspot

    if org is not None:
        ts.org.switch(org)

    r = ts.api.v1.connection_export(guid=connection_guid)
    tml = Connection.loads(r.text)
    tml.guid = connection_guid

    external_tables = [
        {
            "databaseName": table.external_table.db_name,
            "schemaName": table.external_table.schema_name,
            "tableName": table.external_table.table_name,
        }
        for table in tml.connection.table
    ]

    r = ts.api.v1.metadata_details(metadata_type="DATA_SOURCE", guids=[tml.guid])
    d = r.json()["storables"][0]
    i = tml.to_rest_api_v1_metadata()

    r = ts.api.v1.connection_fetch_live_columns(
        guid=tml.guid, tables=external_tables, config=i["configuration"], authentication_type=d["authenticationType"]
    )

    if r.is_error:
        log.error(f"encountered an error fetching columns from [b blue]{tml.name}[/]\n{r.json()}")
        raise typer.Exit(1)

    live_external_data = r.json()
    tables_sync = []
    column_sync = []

    for internal_table in tml.connection.table:
        fqn_name = ".".join(
            [
                internal_table.external_table.db_name,
                internal_table.external_table.schema_name,
                internal_table.external_table.table_name,
            ]
        )

        if fqn_name not in live_external_data:
            log.warning(f"internal table '{fqn_name}' has no external representation in {connection_guid}")
            continue

        out_of_sync = 0

        for column in internal_table.column:
            external_column = next(c for c in live_external_data[fqn_name] if c["name"] == column.external_column)
            column_info = {
                "database": internal_table.external_table.db_name,
                "schema": internal_table.external_table.schema_name,
                "table": internal_table.external_table.table_name,
                "column": column.name,
                "data_type_internal": column.data_type,
                "data_type_external": external_column["type"] if external_column["isLinkedActive"] else "{null}",
                "is_missing_external": not external_column["isLinkedActive"],
            }

            metadata = MetadataColumn(**column_info)

            if metadata.is_out_of_sync:
                out_of_sync += 1
                column_sync.append(metadata)

        if out_of_sync == len(internal_table.column):
            log.info(f"whole table is out of sync: {internal_table.name} ({internal_table.id})")
            tables_sync.append(metadata.fully_qualified_name)

    if not column_sync:
        log.info("[b green]No columns[/] are out of sync with the external database!")
        raise typer.Exit(0)

    bye_column = sum(1 for c in column_sync if c.is_missing_external)
    oos_table = len({c.fully_qualified_name for c in column_sync})
    log.warning(
        f"[b yellow]{len(column_sync) - bye_column} columns out of sync and {bye_column} missing across {oos_table} "
        f"tables in [b blue]{tml.name} ({tml.guid})"
    )

    if syncer is None:
        table = layout.build_table()
        [
            table.renderable.add_row(*column.values)
            for column in column_sync
            if column.fully_qualified_name not in tables_sync
        ]
        rich_console.print(table)

    else:
        syncer.dump("connection-check", data=[column.dict() for column in column_sync])


@app.command(dependencies=[thoughtspot], name="export")
def scriptability_export(
    ctx: typer.Context,
    directory: pathlib.Path = typer.Argument(
        ..., help="directory to save TML to", file_okay=False, resolve_path=True, exists=True
    ),
    tags: str = typer.Option(
        None,
        custom_type=MultipleChoiceType(),
        help="objects marked with tags to export, comma separated",
    ),
    guids: str = typer.Option(
        None,
        custom_type=MultipleChoiceType(),
        help="specific objects to export, comma separated",
    ),
    author: str = typer.Option(None, help="objects authored by this username to export"),
    pattern: str = typer.Option(
        None, help=r"object names which meet a pattern, follows SQL LIKE operator (% as a wildcard)"
    ),
    include_types: str = typer.Option(
        None,
        custom_type=MultipleChoiceType(),
        help="list of types to export: answer, connection, liveboard, table, sqlview, view, worksheet",
    ),
    exclude_types: str = typer.Option(
        None,
        custom_type=MultipleChoiceType(),
        help=(
            "list of types to exclude (overrides include): answer, connection, liveboard, table, sqlview, view, "
            "worksheet"
        ),
    ),
    export_associated: bool = typer.Option(
        False, "--export-associated", help="if specified, also export related content (does not export connections)"
    ),
    org: str = typer.Option(None, help="name or ID of the org to export from"),
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
    path: pathlib.Path = typer.Argument(..., help="Root folder to load TML from", file_okay=False, resolve_path=True),
    guid: str = typer.Option(
        None, help="Loads a specific file.  Assumes all dependencies are met.", file_okay=True, resolve_path=True
    ),
    import_policy: TMLImportPolicy = typer.Option(TMLImportPolicy.validate, help="The import policy type"),
    force_create: bool = typer.Option(False, "--force-create", help="will force a new object to be created"),
    source: str = typer.Option(
        ..., help="the source environment the TML came from", rich_help_panel="GUID Mapping Options"
    ),
    dest: str = typer.Option(
        ..., help="the destination environment the TML is importing into", rich_help_panel="GUID Mapping Options"
    ),
    tags: list[str] = typer.Option([], help="one or more tags to add to the imported content"),
    share_with: list[str] = typer.Option([], help="one or more groups to share the uploaded content with"),
    org: str = typer.Option(None, help="name of org to import to"),
    include_types: Optional[str] = typer.Option(
        None,
        hidden=False,
        custom_type=MultipleChoiceType(),
        help="list of types to export: answer, connection, liveboard, table, sqlview, view, worksheet",
    ),
    exclude_types: Optional[str] = typer.Option(
        None,
        hidden=False,
        custom_type=MultipleChoiceType(),
        help=(
            "list of types to exclude (overrides include): answer, connection, liveboard, table, sqlview, view, "
            "worksheet"
        ),
    ),
    show_mapping: Optional[bool] = typer.Option(default=False, help="show the mapping file"),
):
    """
    Import TML from a file or directory into ThoughtSpot.

    \b
    cs_tools depends on thoughtspot_tml. The GUID file is produced from
    thoughtspot_tml and requires a specific format. For further information on the
    GUID File, see

       https://github.com/thoughtspot/thoughtspot_tml/tree/v2_0_release#environmentguidmapper
    """
    to_import(
        ts=ctx.obj.thoughtspot,
        path=path,
        guid=guid and GUID(guid),
        import_policy=import_policy,
        force_create=force_create,
        source=source,
        dest=dest,
        tags=tags,
        share_with=share_with,
        org=org,
        include_types=include_types,
        exclude_types=exclude_types,
        show_mapping=show_mapping,
    )


@app.command(name="compare")
def scriptability_compare(
    file1: pathlib.Path = typer.Argument(
        ..., help="full path to the first TML file to compare", dir_okay=False, resolve_path=True
    ),
    file2: pathlib.Path = typer.Argument(
        ..., help="full path to the second TML file to compare", dir_okay=False, resolve_path=True
    ),
):
    """
    Compares two TML files for differences.
    """
    compare(file1=file1, file2=file2)
