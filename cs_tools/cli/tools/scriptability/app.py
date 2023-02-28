# DEV NOTE:
#
# Future enhancements:
#   - ability to manipulate objects, such as renaming references to worksheets and tables, token replacement, etc.
#   - add support for tables and connections
#   - add support for importing .zip files
#
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
import logging
import pathlib

import typer

from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import MultipleChoiceType, SyncerProtocolType
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
    def values(self) -> Tuple[str]:
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

    def dict(self) -> Dict[str, str]:
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
    connection_guid: GUID = Opt(..., help="connection GUID"),
    syncer: DSyncer = Opt(
        None,
        custom_type=SyncerProtocolType(),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    )
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

    r = ts.api.metadata_details(metadata_type="DATA_SOURCE", guids=[tml.guid])
    d = r.json()["storables"][0]
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

    live_external_data = r.json()
    tables_sync = []
    column_sync = []

    for internal_table in tml.connection.table:
        fqn_name = ".".join(
            [
                internal_table.external_table.db_name,
                internal_table.external_table.schema_name,
                internal_table.external_table.table_name
            ]
        )

        if fqn_name not in live_external_data:
            log.warning(f"internal table '{fqn_name}' has no external representation in {connection_guid}")
            continue

        out_of_sync = 0

        for idx, column in enumerate(internal_table.column, start=1):
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

        if out_of_sync == idx:
            log.info(f"whole table is out of sync: {internal_table.name} ({internal_table.id})")
            tables_sync.append(metadata.fully_qualified_name)

    if not column_sync:
        log.info("[b green]No columns[/] are out of sync with the external database!")
        raise typer.Exit(0)

    oos_column = len(column_sync)
    oos_table = len({c.fully_qualified_name for c in column_sync})
    log.warning(f"[b yellow]{oos_column} columns across {oos_table} tables are out of sync in [b blue]{tml.name}")

    if syncer is None:
        table = layout.build_table()
        [table.renderable.add_row(*column.values) for column in column_sync if column.fully_qualified_name not in tables_sync]
        rich_console.print(table)

    else:
        syncer.dump(f"connection-rationalize", data=[column.dict() for column in column_sync])


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
    path: pathlib.Path = Arg(
        ..., help="file or directory to load TML from", file_okay=True, resolve_path=True
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
    tml_logs: pathlib.Path = Opt(
        None,
        help="full path to the directory to log sent TML. TML can change during load.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
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
        ts=ctx.obj.thoughtspot,
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
