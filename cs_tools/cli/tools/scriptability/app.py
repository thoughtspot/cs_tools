from __future__ import annotations

import datetime as dt
import json
import logging
import pathlib

import httpx
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


@app.command(name="export", hidden=True, help="This name is deprecated, but kept for discoverability.")
@app.command(name="commit", hidden=True, help="This name implies we're a VCS (nope!), but kept to mirror the git tool.")
@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def checkpoint(
    ctx: typer.Context,
    directory: pathlib.Path = typer.Option(
        ...,
        click_type=custom_types.Directory(),
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
    delete_aware: bool = typer.Option(
        False, "--delete-aware", help="Deletes TML in the mapping if it is not present in this checkpoint."
    ),
    log_errors: bool = typer.Option(False, "--log-errors", help="Log TML errors to the console."),
    org_override: str = typer.Option(None, "--org", help="The Org to switch to before performing actions."),
) -> _types.ExitCode:
    """
    Export TML to a directory.

    Only objects matching ALL Export Options will be exported.

    A mapping file will be created at .mappings/<environment>-guid-mappings.json

      The mapping file contains 4 fields.

        .metadata
          You may add any information to this field, it will be carried forward through deployments.

        .mapping
          Automatically maintained by CS Tools. GUIDs replacements between environments, will apply to TML before deployment.

        .additional_mapping
          You may add additional string replacements to this field, will apply to TML before deployment.

        .history
          Automatically maintained by CS Tools. A log of checkpoints used for merging and deployment.
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
                "cluster" if ts.session_context.user.org_context is None else str(ts.session_context.user.org_context),
            ]
        )

    # SET UP OUR GUID MAPPING.
    directory.joinpath(".mappings").mkdir(parents=True, exist_ok=True)

    mapping_info = local_utils.GUIDMappingInfo.load(path=directory / ".mappings" / f"{environment}-guid-mappings.json")
    mapping_info.metadata.setdefault("cs_tools", {"extract_environment": environment})

    c = workflows.metadata.fetch_all(
        metadata_types=metadata_types,
        pattern=pattern,
        created_by_user_identifiers=authors,
        tag_identifiers=tags,
        http=ts.api,
    )
    _ = api_transformer.ts_metadata_object(data=utils.run_sync(c))

    # FILTER TO JUST THE OBJECTS WE CARE ABOUT.
    _ = [
        metadata_object
        for metadata_object in _
        if local_utils.is_allowed_object(
            metadata_object,
            allowed_types=input_types,
            disallowed_system_users=[] if include_system_owned_content else SYSTEM_USER_GUIDS,
        )
    ]

    # IF THE OBJECT ISN'T IN THIS LIST, BUT IT'S IN THE MAPPING, WE REMOVE IT FROM THE MAPPING.
    if delete_aware:
        incoming_guids = {metadata_object["object_guid"] for metadata_object in _}
        deleting_guids = {guid for guid in mapping_info.mapping if guid not in incoming_guids}

        for guid in deleting_guids:
            mapping_info.mapping.pop(guid)

            if tml_path := next(directory.rglob(f"{guid}*.tml"), None):
                _LOG.debug(f"Deleting orphaned TML {tml_path}")
                tml_path.unlink()

    # BUILD OUR LIST OF EXPORTS.
    coros = [
        workflows.metadata.tml_export(
            guid=metadata_object["object_guid"],
            edoc_format="YAML",
            directory=directory,
            http=ts.api,
        )
        for metadata_object in _
    ]

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

    # DEFINE A CHECKPOINT.
    mapping_info.checkpoint(
        by=f"cs_tools/{__version__}/scriptability/checkpoint",
        mode="EXPORT",
        environment=environment,
        status=table.job_status,
        info={
            "files_expected": len(coros),
            "files_exported": sum(s.status != "ERROR" for s in table.statuses),
        },
    )

    # RECORD THE GUID MAPPING
    mapping_info.save()

    if table.job_status != "OK":
        _LOG.error("One or more TMLs failed to fully export, check the logs or use --log-errors for more details.")
        return 1

    return 0


@app.command(name="import", hidden=True, help="This name is deprecated, but kept for discoverability.")
@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def deploy(
    ctx: typer.Context,
    directory: pathlib.Path = typer.Option(
        ...,
        click_type=custom_types.Directory(),
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
    skip_diff_check: bool = typer.Option(
        False,
        "--skip-diff-check",
        help="Whether to skip the diff check before importing TML.",
        rich_help_panel="TML Import Options",
        hidden=True,
    ),
    org_override: str = typer.Option(None, "--org", help="The Org to switch to before performing actions."),
    log_errors: bool = typer.Option(False, "--log-errors", help="Log TML errors to the console."),
) -> _types.ExitCode:
    """
    Import TML from a directory.

    The mapping file at .mappings/<source-environment>-guid-mappings.json will be used as context.

    A new mapping file will be created at .mappings/<target-environment>-guid-mappings.json.

      The mapping file contains 4 fields.

        .metadata
          You may add any information to this field, it will be carried forward through deployments.

        .mapping
          Automatically maintained by CS Tools. GUIDs replacements between environments, will apply to TML before deployment.

        .additional_mapping
          You may add additional string replacements to this field, will apply to TML before deployment.

        .history
          Automatically maintained by CS Tools. A log of checkpoints used for merging and deployment.
    """
    ts = ctx.obj.thoughtspot

    EPOCH = dt.datetime(year=1970, month=1, day=1, tzinfo=dt.timezone.utc)

    if input_types == ["ALL"]:
        input_types = ["CONNECTION", "TABLE", "VIEW", "SQL_VIEW", "MODEL", "LIVEBOARD", "ANSWER"]  # type: ignore[assignment]

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    try:
        src_mapping_file = directory / ".mappings" / f"{source_environment}-guid-mappings.json"
        tar_mapping_file = directory / ".mappings" / f"{target_environment}-guid-mappings.json"
        assert src_mapping_file.exists(), f"Could not find a guid mapping file at '{src_mapping_file}'"

        # SET UP OUR GUID MAPPING.
        mapping_info = local_utils.GUIDMappingInfo.merge(source=src_mapping_file, target=tar_mapping_file)
        last_import_dt = next((c.at for c in mapping_info.history if c.mode == "IMPORT"), EPOCH)
    except AssertionError as e:
        _LOG.error(f"{e}, have you run [fg-secondary]scriptability checkpoint --environment {source_environment}[/]?")
        return 1
    except json.JSONDecodeError as e:
        _LOG.error("One of your .mappings/<env>-guid-mappings.json is in an invalid state, see logs for details..")
        _LOG.warning(f"Do you have a trailing comma on line {e.lineno - 1}?")
        return 1
    except RuntimeError as e:
        _LOG.error(f"{e}")
        return 1
    except Exception:
        _LOG.debug("Error Info:", exc_info=True)
        _LOG.error("One of your .mappings/<env>-guid-mappings.json may be in an invalid state, see logs for details..")
        return 1

    tmls: dict[_types.GUID, _types.TMLObject] = {}

    for path in directory.rglob("*.tml"):
        last_modified_time = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)

        if deploy_type == "DELTA" and last_modified_time < last_import_dt:
            continue

        TML = thoughtspot_tml.utils.determine_tml_type(path=path)
        tml = TML.load(path=path)
        assert tml.guid is not None, f"Could not find a guid for {path}"

        if tml.tml_type_name.upper() not in input_types:
            continue

        guid = tml.guid
        tmls[guid] = mapping_info.disambiguate(tml=tml, delete_unmapped_guids=True)

    if not tmls:
        _LOG.info(
            f"No TML files found to deploy from directory (Deploy Type: {deploy_type}, Last Seen: {last_import_dt})"
        )
        return 0

    try:
        c = workflows.metadata.tml_import(
            tmls=list(tmls.values()),
            policy=deploy_policy,
            use_async_endpoint=use_async_endpoint,
            wait_for_completion=use_async_endpoint,
            log_errors=False,
            http=ts.api,
        )
        _ = utils.run_sync(c)

    except httpx.HTTPStatusError as e:
        _LOG.error("Could not import TML due to a ThoughtSpot API error, see logs for details..")
        _LOG.debug(f"Full error: {e}", exc_info=True)
        return 1

    table = local_utils.TMLOperations(
        _,
        domain="SCRIPTABILITY",
        op="VALIDATE" if deploy_policy == "VALIDATE_ONLY" else "IMPORT",
        policy=deploy_policy,
    )

    # RECORD A CHECKPOINT.
    mapping_info.checkpoint(
        by=f"cs_tools/{__version__}/scriptability/deploy",
        mode="VALIDATE" if deploy_policy == "VALIDATE_ONLY" else "IMPORT",
        environment=target_environment,
        status=table.job_status,
        info={
            "deploy_type": deploy_type,
            "deploy_policy": deploy_policy,
            "files_expected": len(tmls),
            "files_deployed": 0 if not table.can_map_guids else sum(s.status != "ERROR" for s in table.statuses),
        },
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
    mapping_info.save(new_path=directory / ".mappings" / f"{target_environment}-guid-mappings.json")

    if tags and guids_to_tag:
        c = workflows.metadata.tag_all(guids_to_tag, tags=tags, color="#A020F0", http=ts.api)  # ThoughtSpot Purple :~)
        _ = utils.run_sync(c)

    if table.job_status == "ERROR":
        _LOG.error("One or more TMLs failed to fully deploy, check the logs or use --log-errors for more details.")
        return 1

    if table.job_status == "WARNING":
        _LOG.warning(
            "TMLs imported succesfully with one or more warnings. Check the logs or use --log-errors for more details."
        )
        return 2

    return 0
