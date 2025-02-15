from __future__ import annotations

from collections.abc import Coroutine
import datetime as dt
import logging
import pathlib

import thoughtspot_tml
import typer

from cs_tools import __version__, _types, utils
from cs_tools.api import workflows
from cs_tools.cli import custom_types
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.ux import RICH_CONSOLE, AsyncTyper

from . import (
    api_transformer,
    utils as local_utils,
)

_LOG = logging.getLogger(__name__)
app = AsyncTyper(help="Maintaining TML between your ThoughtSpot Environments.")

_DOCS_MAPPING = "https://developers.thoughtspot.com/docs/deploy-with-tml-apis#guidMapping"


@app.command(name="export", hidden=True)
@app.command(name="commit", hidden=True)
@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def checkpoint(
    ctx: typer.Context,
    directory: pathlib.Path = typer.Option(
        ...,
        click_type=custom_types.Directory(exists=True, make=True),
        help="Directory to save TML files to.",
    ),
    environment: str = typer.Option(
        None,
        help="The name of the env you're exporting TML from.",
        rich_help_panel=f"[link={_DOCS_MAPPING}]GUID Mapping Options[/]",
    ),
    input_types: custom_types.MultipleInput = typer.Option(
        ...,
        "--metadata-types",
        click_type=custom_types.MultipleInput(
            choices=["CONNECTION", "TABLE", "VIEW", "SQL_VIEW", "MODEL", "LIVEBOARD", "ANSWER", "__ALL__"],
        ),
        help="The type of TML(s) to export, comma separated.",
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
    include_system_owned_content: bool = typer.Option(
        False,
        "--include-system",
        help="Whether or not to include content owned by built-in Administrator accounts.",
        rich_help_panel="TML Export Options",
    ),
    log_errors: bool = typer.Option(False, "--log-errors", help="Log TML errors to the console."),
    org_override: str = typer.Option(None, "--org", help="The org to export TML from."),
) -> _types.ExitCode:
    """
    Export TML to a directory.

    Only objects matching ALL Export Options will be exported.

    A mapping file will be created at .mappings/<environment>-guid-mappings.json
    """
    ts = ctx.obj.thoughtspot

    SYSTEM_USER_GUIDS = ts.session_context.thoughtspot.system_users.values()

    if input_types == ["ALL"]:
        input_types = ["CONNECTION", "TABLE", "VIEW", "SQL_VIEW", "MODEL", "LIVEBOARD", "ANSWER"]  # type: ignore[assignment]

    metadata_types = {_types.lookup_metadata_type(_, mode="FRIENDLY_TO_API") for _ in input_types}

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    if environment is None:
        environment = "_".join(
            [
                ts.session_context.thoughtspot.cluster_name,
                ts.session_context.user.org_context or "primary",
            ]
        )

    # SET UP OUR GUID MAPPING.
    directory.joinpath(".mappings").mkdir(parents=True, exist_ok=True)
    mapping_info = local_utils.GUIDMappingInfo.load(path=directory / ".mappings" / f"{environment}-guid-mappings.json")
    mapping_info.metadata["checkpoint"] = local_utils.MappingMetadataCheckpoint.parse_obj(
        {
            **mapping_info.metadata.get("checkpoint", {}),
            # OVERRIDES
            "by": f"cs_tools/{__version__}/scriptability/checkpoint",
            "at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
            "counter": mapping_info.metadata.get("checkpoint", {}).get("counter", 0) + 1,
            "last_export": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        }
    ).model_dump()

    c = workflows.metadata.fetch_all(
        metadata_types=metadata_types,
        pattern=pattern,
        created_by_user_identifiers=authors,
        tag_identifiers=tags,
        http=ts.api,
    )
    _ = api_transformer.ts_metadata_object(data=utils.run_sync(c))

    coros: list[Coroutine] = []

    for metadata_object in _:
        if not local_utils.is_allowed_object(
            metadata_object,
            allowed_types=input_types,
            disallowed_system_users=[] if include_system_owned_content else SYSTEM_USER_GUIDS,
        ):
            continue

        coros.append(
            workflows.metadata.tml_export(
                guid=metadata_object["object_guid"],
                edoc_format="YAML",
                directory=directory,
                http=ts.api,
            )
        )

    # ANY FASTER THAN 4 CONCURRENT DOWNLOADS AND WE WILL STRESS ATLAS OUT :')
    c = utils.bounded_gather(*coros, max_concurrent=4)  # type: ignore[assignment]
    _ = utils.run_sync(c)

    table = local_utils.TMLOperations(_, domain="SCRIPTABILITY", op="EXPORT")

    if ts.session_context.environment.is_ci:
        _LOG.info(table)
    else:
        RICH_CONSOLE.print(table)

    for response in table.statuses:
        if log_errors and response.status != "OK":
            assert response.message is not None, "TML warning/errors should always come with a raw.error_message."
            _LOG.log(
                level=logging.getLevelName(response.status),
                msg="\n".join([response.metadata_guid, response.message]),
            )

        if response.status != "ERROR":
            mapping_info.mapping.setdefault(response.metadata_guid, None)

    # RECORD THE GUID MAPPING
    mapping_info.save()

    if table.job_status != "OK":
        _LOG.error("One or more TMLs failed to fully export, check the logs or use --log-errors for more details.")
        return 1

    return 0


@app.command(name="import", hidden=True)
@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def deploy(
    ctx: typer.Context,
    directory: pathlib.Path = typer.Option(
        ...,
        click_type=custom_types.Directory(exists=True),
        help="Directory to load TML files from.",
    ),
    tags: custom_types.MultipleInput = typer.Option(
        None,
        click_type=custom_types.MultipleInput(sep=","),
        help="TML will be tagged with these name(s), comma separated.",
        show_default=False,
    ),
    source_environment: str = typer.Option(
        ...,
        help="The name of the env you're deploying TML [fg-secondary]from[/].",
        rich_help_panel=f"[link={_DOCS_MAPPING}]GUID Mapping Options[/]",
    ),
    target_environment: str = typer.Option(
        ...,
        help="The name of the [fg-secondary]new env[/] you're deploying TML [fg-secondary]to[/].",
        rich_help_panel=f"[link={_DOCS_MAPPING}]GUID Mapping Options[/]",
    ),
    input_types: custom_types.MultipleInput = typer.Option(
        "ALL",
        "--metadata-types",
        click_type=custom_types.MultipleInput(
            choices=["CONNECTION", "TABLE", "VIEW", "SQL_VIEW", "MODEL", "LIVEBOARD", "ANSWER", "__ALL__"],
        ),
        help="The type of TML to deploy, comma separated.",
        rich_help_panel="TML Import Options",
    ),
    deploy_type: _types.TMLDeployType = typer.Option(
        "DELTA",
        help="If all TML or only modified files since the last known IMPORT should be deployed.",
        rich_help_panel="TML Import Options",
    ),
    deploy_policy: _types.TMLImportPolicy = typer.Option(
        "ALL_OR_NONE",
        help="Whether to accept any errors during IMPORT.",
        rich_help_panel="TML Import Options",
    ),
    use_async_endpoint: bool = typer.Option(
        False,
        "--async",
        help="Whether to use the new metadata/tml/async/import endpoint or not (v10.5.0+).",
        rich_help_panel="TML Import Options",
        hidden=True,
    ),
    org_override: str = typer.Option(None, "--org", help="The org to import TML to."),
    log_errors: bool = typer.Option(False, "--log-errors", help="Log TML errors to the console."),
) -> _types.ExitCode:
    """Import TML from a directory."""
    ts = ctx.obj.thoughtspot

    EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc).isoformat()

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    try:
        mapping_file = directory / ".mappings" / f"{source_environment}-guid-mappings.json"
        assert mapping_file.exists(), f"Could not find a guid mapping file at '{mapping_file}'"

        # SET UP OUR GUID MAPPING.
        mapping_info = local_utils.GUIDMappingInfo.load(path=mapping_file)
        last_import = dt.datetime.fromisoformat(mapping_info.metadata["checkpoint"].get("last_import", None) or EPOCH)
        mapping_info.metadata["checkpoint"]["mapped_to"] = f"{target_environment}-guid-mappings.json"

        mapping_info.metadata["checkpoint"]["by"] = f"cs_tools/{__version__}/scriptability/deploy"
        mapping_info.metadata["checkpoint"]["at"] = dt.datetime.now(tz=dt.timezone.utc).isoformat()
        mapping_info.metadata["checkpoint"]["counter"] += 1
        mapping_info.metadata["checkpoint"]["last_import"] = dt.datetime.now(tz=dt.timezone.utc).isoformat()
    except AssertionError as e:
        _LOG.error(f"{e}, have you run [fg-secondary]scriptability checkpoint --environment {source_environment}[/]?")
        return 1
    except KeyError:
        _LOG.error("Metadata mapping checkpoint is in an invalid state!")
        return 1

    tmls: dict[_types.GUID, _types.TMLObject] = {}

    for path in directory.rglob("*.tml"):
        last_modified_time = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)

        if deploy_type == "DELTA" and last_modified_time < last_import:
            continue

        TML = thoughtspot_tml.utils.determine_tml_type(path=path)
        tml = TML.load(path=path)
        assert tml.guid is not None, f"Could not find a guid for {path}"

        if input_types != ["ALL"] and tml.tml_type_name.upper() not in input_types:
            continue

        guid = tml.guid
        tmls[guid] = mapping_info.disambiguate(tml=tml, delete_unmapped_guids=True)

    if not tmls:
        _LOG.info(f"No TML files found to deploy from directory (Deploy Type: {deploy_type}, Last Seen: {last_import})")
        return 0

    # Silence the cs_tools metadata workflow logger since we've asked the User if they want logged feedback.
    logging.getLogger("cs_tools.api.workflows.metadata").setLevel(logging.CRITICAL)

    c = workflows.metadata.tml_import(
        tmls=list(tmls.values()),
        use_async_endpoint=use_async_endpoint,
        policy=deploy_policy,
        http=ts.api,
    )
    _ = utils.run_sync(c)

    table = local_utils.TMLOperations(
        _,
        domain="SCRIPTABILITY",
        op="VALIDATE" if deploy_policy == "VALIDATE_ONLY" else "IMPORT",
        policy=deploy_policy,
    )

    # INJECT ERRORS WITH MORE INFO FOR OUR USERS CLARITY.
    for original_guid, response in zip(tmls, table.statuses):
        if response.status == "ERROR":
            response.metadata_name = tmls[original_guid].name
            response.metadata_type = tmls[original_guid].tml_type_name.upper()

    if ts.session_context.environment.is_ci:
        _LOG.info(table)
    else:
        RICH_CONSOLE.print(table)

    guids_to_tag: set[_types.GUID] = set()

    for original_guid, response in zip(tmls, table.statuses):
        if log_errors and response.status != "OK":
            assert response.message is not None, "TML warning/errors should always come with a raw.error_message."
            n = len(response.cleaned_messages)
            s = "" if n == 1 else "s"
            _LOG.log(
                level=logging.getLevelName(response.status),
                msg="\n".join([f"{response.metadata_guid} >> Found {n} issue{s}.\n", response.message, ""]),
            )

        if table.can_map_guids and response.metadata_guid is not None:
            mapping_info.map_guid(old=original_guid, new=response.metadata_guid, disallow_overriding=True)
            guids_to_tag.add(response.metadata_guid)

    # RECORD THE GUID MAPPING
    mapping_info.save()

    if tags and guids_to_tag:
        c = workflows.metadata.tag_all(guids_to_tag, tags=tags, color="#A020F0", http=ts.api)  # ThoughtSpot Purple :~)
        _ = utils.run_sync(c)

    if table.job_status == "ERROR":
        _LOG.error("One or more TMLs failed to fully deploy, check the logs or use --log-errors for more details.")
        return 1

    return 0
