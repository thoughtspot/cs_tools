from __future__ import annotations

from collections.abc import Coroutine
from typing import Literal
import collections
import datetime as dt
import logging
import pathlib
import zoneinfo

from thoughtspot_tml import Table
from thoughtspot_tml.utils import determine_tml_type
import httpx
import sqlalchemy as sa
import typer

from cs_tools import _types, utils
from cs_tools.api import workflows
from cs_tools.cli import (
    custom_types,
    progress as px,
)
from cs_tools.cli.dependencies import ThoughtSpot, depends_on
from cs_tools.cli.ux import AsyncTyper
from cs_tools.sync.base import DatabaseSyncer, Syncer
from cs_tools.sync.sqlite.syncer import SQLite

from . import api_transformer, models

log = logging.getLogger(__name__)
app = AsyncTyper(help="""Explore your ThoughtSpot metadata, in ThoughtSpot!""")


def _ensure_external_mapping(tml: _types.TML, *, connection_info: dict[str, str]) -> _types.TML:
    """Remap TML object to match the external database."""
    if not isinstance(tml, Table):
        return tml

    identity_translator = str.upper if "SNOWFLAKE" in connection_info["dialect"] else str.casefold

    # DATABASE and SCHEMA are taken as-is.
    tml.table.db = connection_info["database"]
    tml.table.schema = connection_info["schema"]

    # TABLE names are translated to UPPERCASE or lowercase depending on dialect.
    tml.table.db_table = identity_translator(tml.table.db_table)

    # COLUMN names are translated to UPPERCASE or lowercase depending on dialect.
    for column in tml.table.columns:
        column.db_column_name = identity_translator(column.db_column_name)

    # REMOVE THE CONNECTION GUID IF WE ARE USING FALCON
    tml.table.connection.name = None if connection_info["dialect"] == "FALCON" else connection_info["name"]
    tml.table.connection.fqn = None if connection_info["dialect"] == "FALCON" else connection_info["guid"]

    return tml


def _is_in_current_org(metadata_object, *, current_org: int) -> bool:
    """Determine if this object belongs in this org."""
    return current_org in (metadata_object["metadata_header"].get("orgIds", None) or [0])


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def deploy(
    ctx: typer.Context,
    cnxn_guid: _types.GUID = typer.Option(
        ...,
        "--connection-guid",
        help="If deploying to Falcon, use [fg-secondary]falcon[/], otherwise find your GUID in the Connection URL.",
    ),
    database: str = typer.Option(
        ...,
        help=(
            "If deploying to Falcon, use [fg-secondary]cs_tools[/], otherwise use the database name holding Searchable "
            "data."
        ),
    ),
    schema: str = typer.Option(
        ...,
        help=(
            "If deploying to Falcon, use [fg-secondary]falcon_default_schema[/], otherwise use the name of the schema "
            "holding Searchable data."
        ),
    ),
    org_override: str = typer.Option(None, "--org", help="The Org to switch to before performing actions."),
    export: pathlib.Path = typer.Option(
        None,
        click_type=custom_types.Directory(exists=False, make=True),
        help="Download the TML of the SpotApp instead of deploying.",
    ),
) -> _types.ExitCode:
    """Deploy the Searchable SpotApp."""
    ts = ctx.obj.thoughtspot

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.switch_org(org_id=org_override)

    TOOL_TASKS = [
        px.WorkTask(id="CONNECTION", description="Getting details for data source"),
        px.WorkTask(id="CUSTOMIZE", description="Customizing Searchable Model to your cluster"),
        px.WorkTask(id="DEPLOY", description="Deploying TML to ThoughtSpot"),
    ]

    with px.WorkTracker("Deploying Searchable", tasks=TOOL_TASKS) as tracker:
        with tracker["CONNECTION"]:
            connection = ""
            db_dialect = ""

            if cnxn_guid.lower() == "falcon":
                db_dialect = "FALCON"

            else:
                c = ts.api.metadata_search(guid=cnxn_guid)
                r = utils.run_sync(c)
                _ = r.json()

                try:
                    d = next(iter(_))
                except StopIteration:
                    log.error(f"Could not find a connection with guid {cnxn_guid}")
                    return 1
                else:
                    connection = d["metadata_name"]
                    db_dialect = d["metadata_header"]["type"]

        with tracker["CUSTOMIZE"]:
            HERE = pathlib.Path(__file__).parent
            tmls: list[_types.TML] = []

            connection_info = {
                "dialect": db_dialect,
                "name": connection,
                "guid": cnxn_guid,
                "database": database,
                "schema": schema,
            }

            # LOAD THE BUNDLED TML AND CUSTOMIZE IT TO THE EXTERNAL DATABASE
            for path in HERE.glob("**/*.tml"):
                tml = determine_tml_type(path=path).load(path=path)
                tml = _ensure_external_mapping(tml, connection_info=connection_info)

                # ENFORCE THOUGHTSPOT METADATA TO BE IN UPPERCASE (in case the admin imported the tables already)
                if isinstance(tml, Table):
                    tml.table.name = tml.table.name.upper()

                # fmt: off
                falcon_and_tsbi_table = "FALCON"     in db_dialect and "TS_BI_SERVER.table.tml" in path.name
                embrace_and_tsbi_view = "FALCON" not in db_dialect and "TS_BI_SERVER.view.tml"  in path.name
                # fmt: on

                # NO NEED TO REPLICATE TS_BI_SERVER IN FALCON, WE'LL USE A SAGE VIEW INSTEAD.
                if falcon_and_tsbi_table or embrace_and_tsbi_view:
                    continue

                # ENFORCE FALCON CLUSTER GUID
                if "FALCON" in db_dialect and "TS_BI_SERVER.view.tml" in path.name:
                    tml.view.formulas[-1].expr = f"'{ts.session_context.thoughtspot.cluster_id}'"

                tmls.append(tml)

                if export is not None:
                    tml.dump(path=export.joinpath(path.name))  # type: ignore[attr-defined]

        with tracker["DEPLOY"]:
            if export is not None:
                return 0

            try:
                c = workflows.metadata.tml_import(tmls=tmls, policy="ALL_OR_NONE", timeout=60 * 15, http=ts.api)
                d = utils.run_sync(c)
            except httpx.HTTPError as e:
                log.error(f"Failed to call metadata/tml/import.. {e}")
                return 1

            for tml_import_info in d:
                idx = tml_import_info["request_index"]
                tml = tmls[idx]
                tml_type = tml.tml_type_name.upper()

                if tml_import_info["response"]["status"]["status_code"] == "OK":
                    log.info(f"{tml_type} '{tml.name}' successfully imported")

    return 0


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def audit_logs(
    ctx: typer.Context,
    syncer: Syncer = typer.Option(
        ...,
        click_type=custom_types.Syncer(models=[models.AuditLogs]),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    last_k_days: int = typer.Option(1, help="how many days of audit logs to fetch", min=1, max=30),
    window_end: Literal["NOW", "TODAY_START_UTC", "TODAY_START_LOCAL"] = typer.Option(
        "NOW", help="how to track events through time"
    ),
) -> _types.ExitCode:
    """
    Extract audit logs from your ThoughtSpot platform.

    ThoughtSpot's retention policy for audit logs is 30 days.
    """
    ts = ctx.obj.thoughtspot

    if window_end == "NOW":
        utc_terminal_end = dt.datetime.now(tz=dt.timezone.utc)

    if window_end == "TODAY_START_UTC":
        utc_terminal_end = dt.datetime.now(tz=dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    if window_end == "TODAY_START_LOCAL":
        utc_terminal_end = (
            dt.datetime.now(tz=dt.timezone.utc)
            .astimezone(tz=ts.session_context.thoughtspot.tz)
            .replace(hour=0, minute=0, second=0, microsecond=0)
        )

    TOOL_TASKS = [
        px.WorkTask(id="COLLECT", description="Fetching data from ThoughtSpot"),
        px.WorkTask(id="CLEAN", description="Transforming API results"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {syncer.name}"),
    ]

    with px.WorkTracker("Fetching Audit Logs Data", tasks=TOOL_TASKS) as tracker:
        with tracker["COLLECT"]:
            _: list[_types.APIResult] = []

            for days in range(last_k_days):
                beg = utc_terminal_end - dt.timedelta(days=days + 1)
                end = utc_terminal_end - dt.timedelta(days=days)
                c = ts.api.logs_fetch(utc_start=beg, utc_end=end)
                r = utils.run_sync(c)

                if r.is_error:
                    log.error("Failed to call the Audit Logs API, see logs for details..")
                    log.debug(f"API Response:\n{r.text}")
                    return 1

                _.append(r.json())

        with tracker["CLEAN"]:
            d = api_transformer.ts_audit_logs(data=_, cluster=ts.session_context.thoughtspot.cluster_id)

        with tracker["DUMP_DATA"]:
            syncer.dump("ts_audit_logs", data=d)

    return 0


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def bi_server(
    ctx: typer.Context,
    syncer: Syncer = typer.Option(
        ...,
        click_type=custom_types.Syncer(models=[models.BIServer]),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    from_date: custom_types.Date = typer.Option(..., help="inclusive lower bound of rows to select from TS: BI Server"),
    to_date: custom_types.Date = typer.Option(..., help="inclusive upper bound of rows to select from TS: BI Server"),
    org_override: str = typer.Option(None, "--org", help="The Org to switch to before performing actions."),
    compact: bool = typer.Option(True, "--compact / --full", help="If compact, add  [User Action] != {null} 'invalid'"),
) -> _types.ExitCode:
    """
    Extract usage statistics from your ThoughtSpot platform.

    To extract one day of data, set [b cyan]--from-date[/] and [b cyan]--to-date[/] to the same value.
    \b
    Fields extracted from TS: BI Server
        - incident id           - timestamp detailed    - url
        - http response code    - browser type          - client type
        - client id             - answer book guid      - viz id
        - user id               - user action           - query text
        - response size         - latency (us)          - database latency (us)
        - impressions
    """
    assert isinstance(from_date, dt.date), f"Could not coerce from_date '{from_date}' to a date."
    assert isinstance(to_date, dt.date), f"Could not coerce to_date '{to_date}' to a date."
    ts = ctx.obj.thoughtspot

    CLUSTER_UUID = ts.session_context.thoughtspot.cluster_id

    # DEV NOTE: @boonhapus, 2025/02/18
    #   BI Server on SaaS is held in ThoughtSpot's multi-tenant Snowflake database,
    #   which is set to UTC, whereas BI Server on Software is held in Falcon and set to
    #   whatever timezone the cluster is.
    TZ_UTC = zoneinfo.ZoneInfo("UTC")
    TS_BI_TIMEZONE = TZ_UTC if ts.session_context.thoughtspot.is_cloud else ts.session_context.thoughtspot.timezone

    if syncer.protocol == "falcon":
        log.error("Falcon Syncer is not supported for TS: BI Server reflection.")
        models.BIServer.__table__.drop(syncer.engine)
        return 1

    if (to_date - from_date) > dt.timedelta(days=31):  # type: ignore[operator]
        log.warning("Due to how the Search API functions, it's recommended to request no more than 1 month at a time.")

    # DEV NOTE: @boonhapus
    # As of 9.10.0.cl , TS: BI Server only resides in the Primary Org(0), so switch to it
    if ts.session_context.thoughtspot.is_orgs_enabled:
        ts.switch_org(org_id=0)

    if org_override is not None:
        c = workflows.metadata.fetch_one(identifier=org_override, metadata_type="ORG", attr_path="id", http=ts.api)
        _ = utils.run_sync(c)
        org_override = _

    SEARCH_DATA_DATE_FMT = "%m/%d/%Y"
    SEARCH_TOKENS = (
        "[incident id] [timestamp].'detailed' [url] [http response code] "
        "[browser type] [browser version] [client type] [client id] [answer book guid] "
        "[viz id] [user id] [user action] [query text] [response size] [latency (us)] "
        "[database latency (us)] [impressions] [timestamp] != 'today'"
        # FOR DATA QUALITY PURPOSES
        + " [incident id] != [incident id].{null}"
        # CONDITIONALS BASED ON CLI OPTIONS OR ENVIRONMENT
        + ("" if not compact else " [user action] != [user action].invalid [user action].{null}")
        + ("" if from_date is None else f" [timestamp] >= '{from_date.strftime(SEARCH_DATA_DATE_FMT)}'")
        + ("" if to_date is None else f" [timestamp] <= '{to_date.strftime(SEARCH_DATA_DATE_FMT)}'")
        + ("" if not ts.session_context.thoughtspot.is_orgs_enabled else " [org id]")
        + ("" if org_override is None else f" [org id] = {org_override}")
    )

    TOOL_TASKS = [
        px.WorkTask(id="SEARCH", description="Fetching data from ThoughtSpot"),
        px.WorkTask(id="CLEAN", description="Transforming API results"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {syncer.name}"),
    ]

    with px.WorkTracker("Fetching TS: BI Server Data", tasks=TOOL_TASKS) as tracker:
        with tracker["SEARCH"]:
            c = workflows.search(worksheet="TS: BI Server", query=SEARCH_TOKENS, timezone=TS_BI_TIMEZONE, http=ts.api)
            _ = utils.run_sync(c)

        with tracker["CLEAN"]:
            d = api_transformer.ts_bi_server(data=_, cluster=CLUSTER_UUID)

        with tracker["DUMP_DATA"]:
            syncer.dump("ts_bi_server", data=d)

    return 0


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def metadata(
    ctx: typer.Context,
    # tables: List[str] = typer.Option(None, help="table names to collect data on, can be specified multiple times"),
    include_column_access: bool = typer.Option(
        False,
        "--include-column-access",
        help="if specified, include security controls for Column Level Security as well",
    ),
    org_override: str = typer.Option(None, "--org", help="The Org to switch to before performing actions."),
    syncer: Syncer = typer.Option(
        ...,
        click_type=custom_types.Syncer(models=models.METADATA_MODELS),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
) -> _types.ExitCode:
    """
    Extract metadata from your ThoughtSpot platform.

    \b
    See the full data model extract at the link below:
      [url]https://thoughtspot.github.io/cs_tools/cs-tools/searchable[/]
    """
    ts = ctx.obj.thoughtspot

    if not ts.session_context.user.is_admin:
        log.warning("Searchable is meant to be run from an Admin-level context, your results may vary..")

    temp = SQLite(
        database_path=ts.config.temp_dir / "temp.db",
        pragma_speedy_inserts=True,
        models=models.METADATA_MODELS,
        load_strategy="UPSERT",
    )

    # Silence the intermediate logger.
    logging.getLogger("cs_tools.sync.sqlite.syncer").setLevel(logging.CRITICAL)

    TOOL_TASKS = [
        px.WorkTask(id="PREPARING", description="Preparing for data collection"),
        px.WorkTask(id="ORGS_COUNT", description="Collecting data from ThoughtSpot"),
        px.WorkTask(id="TS_ORG", description="  Fetching [fg-secondary]ORG[/] data"),
        px.WorkTask(id="TS_GROUP", description="  Fetching [fg-secondary]GROUP[/] data"),
        px.WorkTask(id="TS_PRIVILEGE", description="  Fetching [fg-secondary]PRIVILEGE[/] data"),
        px.WorkTask(id="TS_USER", description="  Fetching [fg-secondary]USER[/] data"),
        px.WorkTask(id="TS_TAG", description="  Fetching [fg-secondary]TAG[/] data"),
        px.WorkTask(id="TS_METADATA", description="  Fetching [fg-secondary]METADATA[/] data"),
        px.WorkTask(id="TS_COLUMN", description="  Fetching [fg-secondary]COLUMN[/] data"),
        px.WorkTask(id="TS_DEPENDENT", description="  Fetching [fg-secondary]DEPENDENT[/] data"),
        px.WorkTask(id="TS_ACCESS", description="  Fetching [fg-secondary]ACCESS[/] data"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {syncer.name}"),
    ]

    with px.WorkTracker("", tasks=TOOL_TASKS) as tracker:
        with tracker["PREPARING"]:
            CLUSTER_UUID = ts.session_context.thoughtspot.cluster_id

            # FETCH ALL ORG IDs WE'LL NEED TO COLLECT FROM
            if ts.session_context.thoughtspot.is_orgs_enabled:
                c = ts.api.orgs_search()
                r = utils.run_sync(c)
                orgs = [_ for _ in r.json() if org_override is None or _["name"].casefold() == org_override.casefold()]
            else:
                orgs = [{"id": 0, "name": "ThoughtSpot"}]

            if not orgs:
                log.error(f"Could not find any orgs with name '{org_override}' to collect data from.")
                return 1

            tracker["ORGS_COUNT"].total = len(orgs)

            # DUMP CLUSTER DATA
            d = api_transformer.ts_cluster(data=ts.session_context)
            temp.dump(models.Cluster.__tablename__, data=d)

        tracker["ORGS_COUNT"].start()

        # LOOP THROUGH EACH ORG COLLECTING DATA
        if org_override is not None:
            collect_info = True
        else:
            collect_info = False

        for org in orgs:
            tracker.title = f"Fetching Data in [fg-secondary]{org['name']}[/] (Org {org['id']})"
            seen_guids: dict[_types.APIObjectType, set[_types.GUID]] = collections.defaultdict(set)
            seen_columns: list[list[_types.GUID]] = []
            # TODO: REMOVE AFTER 10.3.0.SW is n-1 (see COMPAT_GUIDS ref below.)
            seen_group_guids: set[_types.GUID] = set()

            with tracker["TS_ORG"]:
                if not ts.session_context.thoughtspot.is_orgs_enabled:
                    _ = [{"id": 0, "name": "ThoughtSpot", "description": "Your cluster is not orgs enabled."}]
                else:
                    ts.switch_org(org_id=org["id"])
                    c = ts.api.orgs_search()
                    r = utils.run_sync(c)
                    _ = r.json()

                # DUMP ORG DATA
                d = api_transformer.ts_org(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.Org.__tablename__, data=d)

            with tracker["TS_GROUP"]:
                c = ts.api.groups_search_v1()
                r = utils.run_sync(c)
                _ = r.json()

                # commenting out calling of v2 api for CWT customer
                # c = workflows.paginator(ts.api.groups_search, record_size=5_000, timeout=60 * 15)
                # _ = utils.run_sync(c)

                # DUMP GROUP DATA
                d = api_transformer.to_group_v1(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.Group.__tablename__, data=d)

                # TODO: REMOVE AFTER 10.3.0.SW is n-1 (see COMPAT_GUIDS ref below.)
                seen_group_guids.update([group["group_guid"] for group in d])

                # DUMP GROUP->GROUP_MEMBERSHIP DATA
                d = api_transformer.to_group_membership(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.GroupMembership.__tablename__, data=d)

            with tracker["TS_PRIVILEGE"]:
                # TODO: ROLE->PRIVILEGE DATA.
                # TODO: GROUP->ROLE DATA.

                # DUMP GROUP->PRIVILEGE DATA
                d = api_transformer.to_group_privilege(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.GroupPrivilege.__tablename__, data=d)

            if org["id"] == 0 or collect_info:
                with tracker["TS_USER"]:
                    c = workflows.paginator(ts.api.users_search, record_size=5_000, timeout=60 * 15)
                    _ = utils.run_sync(c)

                    # DUMP USER DATA
                    d = api_transformer.ts_user(data=_, cluster=CLUSTER_UUID)
                    temp.dump(models.User.__tablename__, data=d)

                    # DUMP USER->ORG_MEMBERSHIP DATA
                    d = api_transformer.ts_org_membership(data=_, cluster=CLUSTER_UUID)
                    temp.dump(models.OrgMembership.__tablename__, data=d)

                    # DUMP USER->GROUP_MEMBERSHIP DATA
                    d = api_transformer.ts_group_membership(data=_, cluster=CLUSTER_UUID)
                    temp.dump(models.GroupMembership.__tablename__, data=d)
                collect_info = False
            elif org["id"] != 0:
                log.info(f"Skipping USER data fetch for non-primary org (ID: {org['id']}) as it was already fetched.")

            with tracker["TS_TAG"]:
                c = ts.api.tags_search()
                r = utils.run_sync(c)
                _ = r.json()

                # DUMP TAG DATA
                d = api_transformer.ts_tag(data=_, cluster=CLUSTER_UUID, current_org=org["id"])
                temp.dump(models.Tag.__tablename__, data=d)

            with tracker["TS_METADATA"]:
                c = workflows.metadata.fetch_all(
                    metadata_types=["CONNECTION", "LOGICAL_TABLE", "LIVEBOARD", "ANSWER"], http=ts.api
                )
                _ = utils.run_sync(c)

                # COLLECT GUIDS FOR LATER ON.. THIS WILL BE MORE EFFICIENT THAN metadata.fetch_all MULTIPLE TIMES.
                for metadata in _:
                    if _is_in_current_org(metadata, current_org=org["id"]):
                        seen_guids[metadata["metadata_type"]].add(metadata["metadata_id"])

                # DUMP DATA_SOURCE DATA
                d = api_transformer.ts_data_source(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.DataSource.__tablename__, data=d)

                # DUMP METDATA_OBJECT DATA
                d = api_transformer.ts_metadata_object(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.MetadataObject.__tablename__, data=d)

                # DUMP TAGGED_OBJECT DATA
                d = api_transformer.ts_tagged_object(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.TaggedObject.__tablename__, data=d)

            with tracker["TS_COLUMN"]:
                # USE include_hidden_objects=True BECAUSE HIDDEN COLUMNS ON A LOGICAL_TABLE AREN'T RETURNED WITHOUT IT.
                g = {"LOGICAL_TABLE": seen_guids["LOGICAL_TABLE"]}
                c = workflows.metadata.fetch(
                    typed_guids=g, include_details=True, include_hidden_objects=True, http=ts.api
                )
                _ = utils.run_sync(c)

                # COLLECT GUIDS FOR LATER ON.. THIS WILL BE MORE EFFICIENT THAN metadata.fetch_all MULTIPLE TIMES.
                for metadata in _:
                    if _is_in_current_org(metadata, current_org=org["id"]):
                        seen_guids["CONNECTION"].add(metadata["metadata_detail"]["dataSourceId"])

                        if not metadata["metadata_detail"]["columns"]:
                            log.warning(
                                f"LOGICAL_TABLE '{metadata['metadata_header']['name']}' ({metadata['metadata_id']}) "
                                f"somehow has no columns, skipping.."
                            )
                            continue

                        seen_columns.append([_["header"]["id"] for _ in metadata["metadata_detail"]["columns"]])

                # DUMP METDATA_OBJECT DATA (UPSERT LOGICAL_TABLE with .data_source_guid)
                d = api_transformer.ts_metadata_object(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.MetadataObject.__tablename__, data=d)

                # DUMP METADATA_COLUMN DATA
                d = api_transformer.ts_metadata_column(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.MetadataColumn.__tablename__, data=d)

                # DUMP COLUMN_SYNONYM DATA
                d = api_transformer.ts_column_synonym(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.ColumnSynonym.__tablename__, data=d)

            with tracker["TS_DEPENDENT"]:
                c = workflows.metadata.fetch(
                    typed_guids={"LOGICAL_COLUMN": seen_columns},
                    include_dependent_objects=True,
                    dependent_objects_record_size=-1,
                    http=ts.api,
                )
                _ = utils.run_sync(c)

                # DUMP DEPENDENT_OBJECT DATA
                d = api_transformer.ts_metadata_dependent(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.DependentObject.__tablename__, data=d)

            with tracker["TS_ACCESS"]:
                # TODO: REMOVE AFTER 10.3.0.SW is n-1
                COMPAT_TS_VERSION = ts.session_context.thoughtspot.version
                COMPAT_GUIDS = seen_group_guids

                if include_column_access:
                    seen_guids["LOGICAL_COLUMN"] = seen_columns

                c = workflows.metadata.permissions(
                    typed_guids=seen_guids, compat_ts_version=COMPAT_TS_VERSION, http=ts.api
                )
                _ = utils.run_sync(c)

                # DUMP COLUMN_SYNONYM DATA
                d = api_transformer.ts_metadata_permissions(
                    data=_,
                    compat_ts_version=COMPAT_TS_VERSION,
                    compat_all_group_guids=COMPAT_GUIDS,
                    cluster=CLUSTER_UUID,
                )
                temp.dump(models.SharingAccess.__tablename__, data=d)

            # INCREASE THE PROGRESS BAR SINCE WE'RE DONE WITH THIS ORG
            tracker["ORGS_COUNT"].advance(step=1)

        tracker["ORGS_COUNT"].stop()

        with tracker["DUMP_DATA"]:
            # WRITE ALL THE COMBINED DATA TO THE TARGET SYNCER
            is_truncate_load_strategy = isinstance(syncer, DatabaseSyncer) and syncer.load_strategy == "TRUNCATE"

            for model in models.METADATA_MODELS:
                streamer = temp.read_stream(tablename=model.__tablename__, batch=1_000_000)

                for idx, rows in enumerate(streamer, start=1):
                    if is_truncate_load_strategy:
                        syncer.load_strategy = "TRUNCATE" if idx == 1 else "APPEND"

                    syncer.dump(model.__tablename__, data=rows)

    return 0


@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def tml(
    ctx: typer.Context,
    org_override: str = typer.Option(None, "--org", help="The Org to switch to before performing actions."),
    input_types: custom_types.MultipleInput = typer.Option(
        ...,
        "--metadata-type",
        help="The type of TML to export.",
        click_type=custom_types.MultipleInput(
            choices=["MODEL", "LIVEBOARD", "__CONNECTION__", "__TABLE__", "__VIEW__", "__SQL_VIEW__", "__ANSWER__"]
        ),
    ),
    strategy: Literal["DELTA", "SNAPSHOT"] = typer.Option(
        "DELTA",
        help=(
            "SNAPSHOT fetches all objects, DELTA only fetches modified object since the last snapshot (this option "
            "only works with Database Syncers)"
        ),
    ),
    tml_format: Literal["JSON", "YAML"] = typer.Option("YAML", help="The data format to save the TML data in."),
    directory: pathlib.Path = typer.Option(
        None,
        help="The directory to additionally save TMLs to.",
        click_type=custom_types.Directory(exists=False, make=True),
    ),
    syncer: Syncer = typer.Option(
        ...,
        click_type=custom_types.Syncer(models=[models.MetadataTML]),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
) -> _types.ExitCode:
    """Snapshot your TML to a Syncer."""
    ts = ctx.obj.thoughtspot

    filter_types = set(input_types)

    # ADD SUBTYPES OF COMMON FRIENDLY INPUT TYPES.
    if "TABLE" in input_types:
        filter_types.update(["ONE_TO_ONE_LOGICAL", "USER_DEFINED"])

    if "VIEW" in input_types:
        filter_types.update(["AGGR_WORKSHEET"])

    if "MODEL" in input_types:
        filter_types.update(["WORKSHEET"])

    temp = SQLite(
        database_path=ts.config.temp_dir / "temp.db",
        pragma_speedy_inserts=True,
        models=[models.MetadataTML],
        load_strategy="UPSERT",
    )

    # Silence the intermediate logger.
    logging.getLogger("cs_tools.sync.sqlite.syncer").setLevel(logging.CRITICAL)

    TOOL_TASKS = [
        px.WorkTask(id="PREPARING", description="Preparing for data collection"),
        px.WorkTask(id="ORGS_COUNT", description="Collecting data from ThoughtSpot"),
        px.WorkTask(id="TS_METADATA", description="  Fetching metadata"),
        px.WorkTask(id="EXPORT", description="  Exporting TML data"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {syncer.name}"),
    ]

    with px.WorkTracker("", tasks=TOOL_TASKS) as tracker:
        with tracker["PREPARING"]:
            CLUSTER_UUID = ts.session_context.thoughtspot.cluster_id

            # FETCH ALL ORG IDs WE'LL NEED TO COLLECT FROM
            if ts.session_context.thoughtspot.is_orgs_enabled:
                c = ts.api.orgs_search()
                r = utils.run_sync(c)
                orgs = [_ for _ in r.json() if org_override is None or _["name"].casefold() == org_override.casefold()]
            else:
                orgs = [{"id": 0, "name": "ThoughtSpot"}]

            if not orgs:
                log.error(f"Could not find any orgs with name '{org_override}' to collect data from.")
                return 1

            tracker["ORGS_COUNT"].total = len(orgs)

        tracker["ORGS_COUNT"].start()

        # LOOP THROUGH EACH ORG COLLECTING DATA
        for org in orgs:
            tracker.title = f"Fetching Data in [fg-secondary]{org['name']}[/] (Org {org['id']})"

            if ts.session_context.thoughtspot.is_orgs_enabled:
                ts.switch_org(org_id=org["id"])

            with tracker["TS_METADATA"]:
                metadata_types = {_types.lookup_metadata_type(_, mode="FRIENDLY_TO_API") for _ in input_types}
                c = workflows.metadata.fetch_all(metadata_types=metadata_types, http=ts.api)
                _ = utils.run_sync(c)

                # DISCARD OBJECTS WHICH ARE NOT ALLOWED BASED ON THE INPUT TYPES.
                d = [
                    metadata_object
                    for metadata_object in api_transformer.ts_metadata_object(data=_, cluster=CLUSTER_UUID)
                    if {metadata_object["object_type"], metadata_object["object_subtype"]}.intersection(filter_types)
                ]

                if strategy == "DELTA" and isinstance(syncer, DatabaseSyncer):
                    q = sa.text(f"""SELECT MAX(modified) AS latest_dt FROM {models.MetadataTML.__tablename__}""")

                    if r := syncer.session.execute(q).scalar():
                        latest_dt_naive = r if isinstance(r, dt.datetime) else dt.datetime.fromisoformat(r)
                        latest_dt = latest_dt_naive.astimezone(tz=dt.timezone.utc)
                        d = [_ for _ in d if _["modified"] >= latest_dt or _["created"] >= latest_dt]

            with tracker["EXPORT"]:
                coros: list[Coroutine] = []

                for metadata_object in d:
                    opts = {
                        "directory": directory,
                        "export_schema_version": "V2" if metadata_object["object_subtype"] == "MODEL" else "V1",
                        "edoc_format": tml_format,
                    }
                    c = workflows.metadata.tml_export(guid=metadata_object["object_guid"], **opts, http=ts.api)
                    coros.append(c)

                c = utils.bounded_gather(*coros, max_concurrent=4)
                _ = utils.run_sync(c)

                d = api_transformer.ts_metadata_tml(
                    metadata_info=d, tml_info=_, edoc_format=tml_format, cluster=CLUSTER_UUID, org_id=org["id"]
                )
                temp.dump(models.MetadataTML.__tablename__, data=d)

            # INCREASE THE PROGRESS BAR SINCE WE'RE DONE WITH THIS ORG
            tracker["ORGS_COUNT"].advance(step=1)

        tracker["ORGS_COUNT"].stop()

        with tracker["DUMP_DATA"]:
            # WRITE ALL THE COMBINED DATA TO THE TARGET SYNCER
            is_truncate_load_strategy = isinstance(syncer, DatabaseSyncer) and syncer.load_strategy == "TRUNCATE"
            streamer = temp.read_stream(tablename=models.MetadataTML.__tablename__, batch=1_000_000)

            for idx, rows in enumerate(streamer, start=1):
                if is_truncate_load_strategy:
                    syncer.load_strategy = "TRUNCATE" if idx == 1 else "APPEND"

                syncer.dump(models.MetadataTML.__tablename__, data=rows)

    return 0

@app.command()
@depends_on(thoughtspot=ThoughtSpot())
def ts_ai_stats(
    ctx: typer.Context,
    syncer: Syncer = typer.Option(
        ...,
        click_type=custom_types.Syncer(models=[models.AIStats]),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    from_date: custom_types.Date = typer.Option(..., help="inclusive lower bound of rows to select from TS: BI Server"),
    to_date: custom_types.Date = typer.Option(..., help="inclusive upper bound of rows to select from TS: BI Server"),
    org_override: str = typer.Option(None, "--org", help="The Org to switch to before performing actions."),
    compact: bool = typer.Option(True, "--compact / --full", help="If compact, add  [User Action] != {null} 'invalid'"),
) -> _types.ExitCode:
    """
    Extract query performance metrics for each query made against an external database

    To extract one day of data, set [b cyan]--from-date[/] and [b cyan]--to-date[/] to the same value.
    \b
    Fields extracted from TS: AI and BI Stats
    - Answer Session ID     - Average Query Latency (External)      - Average System Latency (Overall)      - Impressions
    - Connection            - Connection ID                         - DB Auth Type                          - Is System
    - DB Type               - Error Message                         - External Database Query ID            - Is Billable
    - Model                 - Model ID                              - Object                                - Object ID
    - Object Subtype        - Object Type                           - Org                                   - Org ID
    - Query Count           - Query End Time                        - Query Errors                          - Query Start Time
    - Query Status          - SQL Query                             - ThoughtSpot Query ID                  - ThoughtSpot Start Time
    - Total Credits         - Total Nums Rows Fetched               - Trace ID                              - User
    - User Action           - User Action Count                     - User Count                            - User Display Name
    - User ID               - Visualization ID
    """
    assert isinstance(from_date, dt.date), f"Could not coerce from_date '{from_date}' to a date."
    assert isinstance(to_date, dt.date), f"Could not coerce to_date '{to_date}' to a date."
    ts = ctx.obj.thoughtspot

    CLUSTER_UUID = ts.session_context.thoughtspot.cluster_id

    TZ_UTC = zoneinfo.ZoneInfo("UTC")
    TS_AI_TIMEZONE = TZ_UTC if ts.session_context.thoughtspot.is_cloud else ts.session_context.thoughtspot.timezone
    print(f"TS_AI_TIMEZONE -> {TS_AI_TIMEZONE}")

    if syncer.protocol == "falcon":
        log.error("Falcon Syncer is not supported for TS: AI Server reflection.")
        models.AIStats.__table__.drop(syncer.engine)
        return 1

    if (to_date - from_date) > dt.timedelta(days=31):  # type: ignore[operator]
        log.warning("Due to how the Search API functions, it's recommended to request no more than 1 month at a time.")

    # DEV NOTE: @boonhapus
    # As of 9.10.0.cl , TS: BI Server only resides in the Primary Org(0), so switch to it
    if ts.session_context.thoughtspot.is_orgs_enabled:
        ts.switch_org(org_id=0)

    if org_override is not None:
        c = workflows.metadata.fetch_one(identifier=org_override, metadata_type="ORG", attr_path="id", http=ts.api)
        _ = utils.run_sync(c)
        org_override = _

    SEARCH_DATA_DATE_FMT = "%m/%d/%Y"
    SEARCH_TOKENS = (
        "[Query Start Time] [Query Start Time].detailed [Query End Time] [Query End Time].detailed [Org]"
        "[Query Status] [Connection] [User] [Nums Rows Fetched] [ThoughtSpot Query ID] [Is Billable] [ThoughtSpot Start Time]"
        "[ThoughtSpot Start Time].detailed [User Action] [Is System] [Visualization ID] [External Database Query ID] [Query Latency (External)] "
        "[Object] [User ID] [Org ID] [Credits] [Impressions] [Query Count] [Query Errors] [System Latency (Overall)] [User Action Count]"
        "[User Action Count] [User Count] [Answer Session ID] [Connection ID] [DB Auth Type] [DB Type] [Error Message] [Model]"
        "[Model ID] [Object ID] [Object Subtype] [Object Type] [SQL Query] [User Display Name] [Trace ID]"
        "[ThoughtSpot Start Time].detailed [ThoughtSpot Start Time] != 'today'"
        # FOR DATA QUALITY PURPOSES
        # CONDITIONALS BASED ON CLI OPTIONS OR ENVIRONMENT
        + ("" if not compact else " [user action] != [user action].invalid [user action].{null}")
        + ("" if from_date is None else f" [ThoughtSpot Start Time] >= '{from_date.strftime(SEARCH_DATA_DATE_FMT)}'")
        + ("" if to_date is None else f" [ThoughtSpot Start Time] <= '{to_date.strftime(SEARCH_DATA_DATE_FMT)}'")
        + ("" if not ts.session_context.thoughtspot.is_orgs_enabled else " [org id]")
        + ("" if org_override is None else f" [org id] = {org_override}")
    )

    TOOL_TASKS = [
        px.WorkTask(id="SEARCH", description="Fetching data from ThoughtSpot"),
        px.WorkTask(id="CLEAN", description="Transforming API results"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {syncer.name}"),
    ]

    # DEV NOTE: @saurabhsingh1608. 09/15/2025
    # Currently worksheet name is "TS: AI and BI Stats (Beta)" change it in future as need arise

    with px.WorkTracker("Fetching TS: AI and BI Stats", tasks=TOOL_TASKS) as tracker:
        with tracker["SEARCH"]:
            c = workflows.search(worksheet="TS: AI and BI Stats (Beta)", query=SEARCH_TOKENS, timezone=TS_AI_TIMEZONE, http=ts.api)
            _ = utils.run_sync(c)

        with tracker["CLEAN"]:
            d = api_transformer.ts_ai_stats(data=_, cluster=CLUSTER_UUID)

        with tracker["DUMP_DATA"]:
            syncer.dump("ts_ai_stats", data=d)

    return 0