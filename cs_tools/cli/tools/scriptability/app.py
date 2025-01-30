from __future__ import annotations

from collections.abc import Coroutine
import itertools as it
import logging

import typer

from cs_tools import _types, utils
from cs_tools.api import workflows
from cs_tools.cli import (
    custom_types,
)
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper

from . import utils as local_utils

_LOG = logging.getLogger(__name__)
app = AsyncTyper(help="Maintaining TML between your ThoughtSpot Environments.")


@app.command(name="export", hidden=True)
@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def checkpoint(
    ctx: typer.Context,
    directory: custom_types.Directory = typer.Option(..., help="Directory to save TML files to."),
    metadata_type: custom_types.MultipleInput = typer.Option(
        ...,
        click_type=custom_types.MultipleInput(
            choices=["CONNECTION", "ANY_TABLE", "TABLE", "MODEL", "LIVEBOARD", "ANSWER", "__ALL__"]
        ),
        help="The type of TML to export, if not provided, then fetch all of the supported_types.",
        rich_help_panel="TML Export Options",
    ),
    pattern: str = typer.Option(
        None,
        help=r"Object names which meet a pattern, follows SQL LIKE operator (% as a wildcard).",
        rich_help_panel="TML Export Options",
    ),
    authors: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="TML created by these User(s), comma separated.",
        show_default=False,
        rich_help_panel="TML Export Options",
    ),
    tags: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="TML tagged with these name(s), comma separated.",
        show_default=False,
        rich_help_panel="TML Export Options",
    ),
    org_override: str = typer.Option(None, "--org", help="The org to export TML from."),
    log_errors: bool = typer.Option(False, "--log-errors", help="Log TML errors to the console."),
) -> _types.ExitCode:
    """
    Export TML to a directory.

    All export options are combined in AND format.
    """
    ts = ctx.obj.thoughtspot

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    CLI_TYPES_TO_API_TYPES = {
        "ALL": ["CONNECTION", "LOGICAL_TABLE", "LIVEBOARD", "ANSWER"],
        "CONNECTION": ["CONNECTION"],
        "ANY_TABLE": ["LOGICAL_TABLE"],
        "TABLE": ["LOGICAL_TABLE"],
        "MODEL": ["LOGICAL_TABLE"],
        "LIVEBOARD": ["LIVEBOARD"],
        "ANSWER": ["ANSWER"],
    }

    metadata_types = set(it.chain.from_iterable(CLI_TYPES_TO_API_TYPES[_] for _ in metadata_type))

    c = workflows.paginator(
        ts.api.metadata_search,
        guid="",
        metadata=[{"type": _, "name_pattern": pattern} for _ in metadata_types],
        include_headers=True,
        created_by_user_identifiers=authors,
        tag_identifiers=tags,
    )
    _ = utils.run_sync(c)

    coros: list[Coroutine] = []

    for metadata_object in _:
        # TODO: FILTER BASED ON INP TYPE.
        coros.append(
            workflows.metadata.tml_export(
                guid=metadata_object["metadata_id"],
                edoc_format="YAML",
                directory=directory,
                http=ts.api,
            )
        )

    c = utils.bounded_gather(*coros, max_concurrent=4)  # type: ignore[assignment]
    d = utils.run_sync(c)

    table = local_utils.TMLOperations(data=d, domain="SCRIPTABILITY", op="EXPORT")

    if ts.session_context.environment.is_ci:
        _LOG.info(table)
    else:
        RICH_CONSOLE.print(table)

    if log_errors:
        for tml_response in filter(lambda r: r["info"]["status"]["status_code"] != "OK", table.data):
            log_level = logging.WARNING if tml_response["info"]["status"]["status_code"] == "WARNING" else logging.ERROR
            log_line = " - ".join(
                [
                    tml_response["info"]["status"]["status_code"],
                    tml_response["info"]["id"],
                    tml_response["info"]["status"]["error_message"].replace("<br/>", "\n"),
                ]
            )
            _LOG.log(level=log_level, msg=log_line)

    if table.job_status != "OK":
        _LOG.error("One or more TMLs failed to fully export, check the logs or use --log-errors for more details.")
        return 1

    return 0


@app.command(name="import", hidden=True)
@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def deploy(
    ctx: typer.Context,
    directory: custom_types.Directory = typer.Option(..., help="Directory to load TML files from."),
    org_override: str = typer.Option(None, "--org", help="The org to import TML to."),
) -> _types.ExitCode:
    """Import TML from a directory."""
    ts = ctx.obj.thoughtspot

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    #
    # IMPORT TMLS
    #

    if ts.session_context.environment.is_ci:
        _LOG.info("...")
    else:
        RICH_CONSOLE.print("...")

    return 0


# app.add_typer(tmlfsApp, name="tmlfs", help="Commands for working with the TML file system")
# app.add_typer(mappingApp, name="mapping", help="Commands for working with TML GUID mappings")

# @app.command(dependencies=[thoughtspot], name="export")
# def scriptability_export(
#     ctx: typer.Context,
#     directory: pathlib.Path = typer.Argument(
#         ..., help="directory to save TML to", file_okay=False, resolve_path=True, exists=True
#     ),
#     tags: str = typer.Option(
#         None,
#         click_type=MultipleChoiceType(),
#         help="objects marked with tags to export, comma separated",
#     ),
#     guids: str = typer.Option(
#         None,
#         click_type=MultipleChoiceType(),
#         help="specific objects to export, comma separated",
#     ),
#     author: str = typer.Option(None, help="objects authored by this username to export"),
#     pattern: str = typer.Option(
#         None, help=r"object names which meet a pattern, follows SQL LIKE operator (% as a wildcard)"
#     ),
#     include_types: str = typer.Option(
#         None,
#         click_type=MultipleChoiceType(),
#         help="list of types to export: answer, connection, liveboard, table, sqlview, view, worksheet",
#     ),
#     exclude_types: str = typer.Option(
#         None,
#         click_type=MultipleChoiceType(),
#         help=(
#             "list of types to exclude (overrides include): answer, connection, liveboard, table, sqlview, view, "
#             "worksheet"
#         ),
#     ),
#     include_system_content: bool = typer.Option(False, help="include System User content in export"),
#     export_associated: bool = typer.Option(
#         False, "--export-associated", help="if specified, also export related content (does not export connections)"
#     ),
#     org_override: str = typer.Option(None, "--org", help="the org to use, if any"),
# ):
#     """
#     Exports TML from ThoughtSpot.

#     There are different parameters that can impact content to download. At least one
#     needs to be specified.

#     - GUIDs: only content with the specific GUIDs will be downloaded.
#     - filters, e.g tags, author, pattern, include_types, exclude_types.

#     If you specify GUIDs then you can't use any filters.

#     Filters are applied in AND fashion - only items that match all filters will be
#     exported. For example, if you export for the "finance" tag and author "user123",
#     then only content owned by that user with the "finance" tag will be exported.
#     """
#     export(
#         ts=ctx.obj.thoughtspot,
#         path=directory,
#         tags=tags,
#         guids=guids,
#         author=author,
#         pattern=pattern,
#         include_types=include_types,
#         exclude_types=exclude_types,
#         exclude_system_content=not include_system_content,
#         export_associated=export_associated,
#         org=org_override,
#     )


# @app.command(dependencies=[thoughtspot], name="import")
# def scriptability_import(
#     ctx: typer.Context,
#     path: pathlib.Path = typer.Argument(..., help="Root folder to load TML from", file_okay=False, resolve_path=True),
#     guid: str = typer.Option(
#         None, help="Loads a specific file.  Assumes all dependencies are met.", file_okay=True, resolve_path=True
#     ),
#     import_policy: TMLImportPolicy = typer.Option(TMLImportPolicy.validate, help="The import policy type"),
#     force_create: bool = typer.Option(False, "--force-create", help="will force a new object to be created"),
#     source: str = typer.Option(
#         ..., help="the source environment the TML came from", rich_help_panel="GUID Mapping Options"
#     ),
#     dest: str = typer.Option(
#         ..., help="the destination environment the TML is importing into", rich_help_panel="GUID Mapping Options"
#     ),
#     tags: list[str] = typer.Option([], help="one or more tags to add to the imported content"),
#     share_with: list[str] = typer.Option([], help="one or more groups to share the uploaded content with"),
#     org_override: str = typer.Option(None, "--org", help="the org to use, if any"),
#     include_types: Optional[str] = typer.Option(
#         None,
#         hidden=False,
#         click_type=MultipleChoiceType(),
#         help="list of types to export: answer, connection, liveboard, table, sqlview, view, worksheet",
#     ),
#     exclude_types: Optional[str] = typer.Option(
#         None,
#         hidden=False,
#         click_type=MultipleChoiceType(),
#         help=(
#             "list of types to exclude (overrides include): answer, connection, liveboard, table, sqlview, view, "
#             "worksheet"
#         ),
#     ),
#     show_mapping: Optional[bool] = typer.Option(default=False, help="show the mapping file"),
# ):
#     """
#     Import TML from a file or directory into ThoughtSpot.

#     \b
#     cs_tools depends on thoughtspot_tml. The GUID file is produced from
#     thoughtspot_tml and requires a specific format. For further information on the
#     GUID File, see

#        https://github.com/thoughtspot/thoughtspot_tml/tree/v2_0_release#environmentguidmapper
#     """
#     to_import(
#         ts=ctx.obj.thoughtspot,
#         path=path,
#         guid=guid,
#         import_policy=import_policy,
#         force_create=force_create,
#         source=source,
#         dest=dest,
#         tags=tags,
#         share_with=share_with,
#         org=org_override,
#         include_types=include_types,
#         exclude_types=exclude_types,
#         show_mapping=show_mapping,
#     )


# @app.command(name="compare")
# def scriptability_compare(
#     file1: pathlib.Path = typer.Argument(
#         ..., help="full path to the first TML file to compare", dir_okay=False, resolve_path=True
#     ),
#     file2: pathlib.Path = typer.Argument(
#         ..., help="full path to the second TML file to compare", dir_okay=False, resolve_path=True
#     ),
# ):
#     """
#     Compares two TML files for differences.
#     """
#     compare(file1=file1, file2=file2)
