from __future__ import annotations

from typing import Literal
import collections
import datetime as dt
import logging
import pathlib

from thoughtspot_tml import Table
from thoughtspot_tml.utils import determine_tml_type
import httpx
import typer

from cs_tools import types, utils
from cs_tools.api import workflows
from cs_tools.cli import progress as px
from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.types import SyncerProtocolType, TZAwareDateTimeType
from cs_tools.cli.ux import CSToolsApp
from cs_tools.sync.sqlite.syncer import SQLite

from . import api_transformer, models

log = logging.getLogger(__name__)
app = CSToolsApp(help="""Explore your ThoughtSpot metadata, in ThoughtSpot!""")


def _ensure_external_mapping(tml: types.TML, *, connection_info: dict[str, str]) -> types.TML:
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


@app.command(dependencies=[thoughtspot])
def deploy(
    ctx: typer.Context,
    cnxn_guid: types.GUID = typer.Option(
        ...,
        "--connection-guid",
        help="if Falcon, use [b blue]falcon[/], otherwise find your guid in the Connection URL in the Data Workspace",
        show_default=False,
    ),
    database: str = typer.Option(
        ...,
        help="if Falcon, use [b blue]cs_tools[/], otherwise use the name of the database which holds Searchable data",
        show_default=False,
    ),
    schema: str = typer.Option(
        ...,
        help=(
            "if Falcon, use [b blue]falcon_default_schema[/], otherwise use the name of the schema which holds "
            "Searchable data"
        ),
        show_default=False,
    ),
    org_override: str = typer.Option(None, "--org", help="the org to fetch history from"),
    export: pathlib.Path = typer.Option(
        None,
        help="download the TML files of the SpotApp",
        file_okay=False,
        show_default=False,
    ),
) -> types.ExitCode:
    """Deploy the Searchable SpotApp."""
    ts = ctx.obj.thoughtspot

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.org.switch(org=org_override)

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
            tmls: list[TML] = []

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
                    tml.dump(path=export.joinpath(path.name))

        with tracker["DEPLOY"]:
            if export is not None:
                return 0

            # DEV NOTE: @boonhapus, 2022/11/27
            # INCLUDING THE array<TML>, THIS WHOLE BLOCK COULD BECOME AN api.workflow.
            #
            c = ts.api.metadata_tml_import(tmls=[t.dumps() for t in tmls], policy="ALL_OR_NONE", timeout=60 * 15)
            r = utils.run_sync(c)

            try:
                r.raise_for_status()

            except httpx.HTTPError as e:
                log.error(f"Failed to call metadata/tml/import.. {e}")
                return 1

            for tml_import_info in r.json():
                idx = tml_import_info["request_index"]
                tml = tmls[idx]
                tml_type = tml.tml_type_name.upper()

                if tml_import_info["response"]["status"]["status_code"] == "ERROR":
                    errors = tml_import_info["response"]["status"]["error_message"].replace("<br/>", "\n")
                    log.error(f"{tml_type} '{tml.name}' failed to import, ThoughtSpot errors:\n[fg-error]{errors}")
                    continue

                if tml_import_info["response"]["status"]["status_code"] == "WARNING":
                    errors = tml_import_info["response"]["status"]["error_message"].replace("<br/>", "\n")
                    log.warning(f"{tml_type} '{tml.name}' partially imported, ThoughtSpot errors:\n[fg-warn]{errors}")

                if tml_import_info["response"]["status"]["status_code"] == "OK":
                    log.info(f"{tml_type} '{tml.name}' successfully imported")

    return 0


@app.command(dependencies=[thoughtspot])
def audit_logs(
    ctx: typer.Context,
    syncer: DSyncer = typer.Option(
        ...,
        click_type=SyncerProtocolType(models=[models.AuditLogs]),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    last_k_days: int = typer.Option(1, help="how many days of audit logs to fetch", min=1, max=30),
    window_end: Literal["NOW", "TODAY_START_UTC", "TODAY_START_LOCAL"] = typer.Option(
        "NOW", help="how to track events through time"
    ),
) -> types.ExitCode:
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
            _: list[types.APIResult] = []

            for days in range(last_k_days):
                beg = utc_terminal_end - dt.timedelta(days=days + 1)
                end = utc_terminal_end - dt.timedelta(days=days)
                c = ts.api.logs_fetch(utc_start=beg, utc_end=end)
                r = utils.run_sync(c)
                _.append(r.json())

        with tracker["CLEAN"]:
            d = api_transformer.ts_audit_logs(data=_, cluster=ts.session_context.thoughtspot.cluster_id)

        with tracker["DUMP_DATA"]:
            syncer.dump("ts_audit_logs", data=d)

    return 0


@app.command(dependencies=[thoughtspot])
def bi_server(
    ctx: typer.Context,
    syncer: DSyncer = typer.Option(
        ...,
        click_type=SyncerProtocolType(models=models.BISERVER_MODELS),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    from_date: dt.datetime = typer.Option(
        ...,
        click_type=TZAwareDateTimeType(),
        metavar="YYYY-MM-DD",
        help="inclusive lower bound of rows to select from TS: BI Server",
    ),
    to_date: dt.datetime = typer.Option(
        ...,
        click_type=TZAwareDateTimeType(),
        metavar="YYYY-MM-DD",
        help="inclusive upper bound of rows to select from TS: BI Server",
    ),
    org_override: str = typer.Option(None, "--org", help="the org to fetch history from"),
    compact: bool = typer.Option(True, "--compact / --full", help="if compact, exclude NULL and INVALID user actions"),
) -> types.ExitCode:
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
    ts = ctx.obj.thoughtspot

    if syncer.protocol == "falcon":
        log.error("Falcon Syncer is not supported for TS: BI Server reflection.")
        models.BIServer.__table__.drop(syncer.engine)
        return 1

    if (to_date - from_date) > dt.timedelta(days=31):
        log.warning("Due to how the Search API is exposed, it's recommended to request no more than 1 month at a time.")

    # DEV NOTE: @boonhapus
    # As of 9.10.0.cl , TS: BI Server only resides in the Primary Org(0), so switch to it
    if ts.session_context.thoughtspot.is_orgs_enabled:
        ts.config.thoughtspot.default_org = 0
        ts.login()

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
        + ("" if org_override is None else f" [org id] = {ts.org.guid_for(org_override)}")
    )

    TOOL_TASKS = [
        px.WorkTask(id="SEARCH", description="Fetching data from ThoughtSpot"),
        px.WorkTask(id="CLEAN", description="Transforming API results"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {syncer.name}"),
    ]

    with px.WorkTracker("Fetching TS: BI Server Data", tasks=TOOL_TASKS) as tracker:
        with tracker["SEARCH"]:
            c = workflows.search(worksheet="TS: BI Server", query=SEARCH_TOKENS, http=ts.api)
            _ = utils.run_sync(c)

        with tracker["CLEAN"]:
            d = api_transformer.ts_bi_server(data=_, cluster=ts.session_context.thoughtspot.cluster_id)

        with tracker["DUMP_DATA"]:
            syncer.dump("ts_bi_server", data=d)

    return 0


@app.command(dependencies=[thoughtspot])
def metadata(
    ctx: typer.Context,
    # tables: List[str] = typer.Option(None, help="table names to collect data on, can be specified multiple times"),
    include_column_access: bool = typer.Option(
        False,
        "--include-column-access",
        help="if specified, include security controls for Column Level Security as well",
    ),
    org_override: str = typer.Option(None, "--org", help="the org to gather metadata from"),
    syncer: DSyncer = typer.Option(
        ...,
        click_type=SyncerProtocolType(models=models.METADATA_MODELS),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
) -> types.ExitCode:
    """
    Extract metadata from your ThoughtSpot platform.

    \b
    See the full data model extract at the link below:
      [url]https://thoughtspot.github.io/cs_tools/cs-tools/searchable[/]
    """
    ts = ctx.obj.thoughtspot

    if not ts.session_context.user.is_admin:
        log.warning("Searchable is meant to be run from an Admin-level context, your results may vary..")

    temp = SQLite(database_path=ts.config.temp_dir / "temp.db", models=models.METADATA_MODELS, load_strategy="UPSERT")

    # Silence the intermediate logger.
    logging.getLogger("cs_tools.sync.sqlite.syncer").setLevel(logging.CRITICAL)

    TOOL_TASKS = [
        px.WorkTask(id="PREPARING", description="Preparing for data collection"),
        px.WorkTask(id="ORGS_COUNT", description="Collecting data from ThoughtSpot"),
        px.WorkTask(id="TS_ORG", description="  Fetching [fg-secondary]ORG[/] data"),
        px.WorkTask(id="TS_USER", description="  Fetching [fg-secondary]USER[/] data"),
        px.WorkTask(id="TS_GROUP", description="  Fetching [fg-secondary]GROUP[/] data"),
        px.WorkTask(id="TS_PRIVILEGE", description="  Fetching [fg-secondary]PRIVILEGE[/] data"),
        px.WorkTask(id="TS_TAG", description="  Fetching [fg-secondary]TAG[/] data"),
        px.WorkTask(id="TS_METADATA", description="  Fetching [fg-secondary]METADATA[/] data"),
        px.WorkTask(id="TS_COLUMN", description="  Fetching [fg-secondary]COLUMN[/] data"),
        px.WorkTask(id="TS_DEPENDENT", description="  Fetching [fg-secondary]DEPENDENT[/] data"),
        px.WorkTask(id="TS_ACCESS", description="  Fetching [fg-secondary]ACCESS[/] data"),
        px.WorkTask(id="DUMP_DATA", description=f"Sending data to {syncer.name}"),
    ]

    def is_in_current_org(metadata_object, *, current_org: int) -> bool:
        """Determine if this object belongs in this org."""
        return current_org in (metadata_object["metadata_header"].get("orgIds", None) or [0])

    with px.WorkTracker("", tasks=TOOL_TASKS) as tracker:
        with tracker["PREPARING"] as this_task:
            CLUSTER_UUID = ts.session_context.thoughtspot.cluster_id

            if ts.session_context.thoughtspot.is_orgs_enabled:
                c = ts.api.orgs_search()
                r = utils.run_sync(c)
                orgs = [_ for _ in r.json() if org_override is None or _["id"] == org_override]
            else:
                orgs = [{"id": 0, "name": "ThoughtSpot"}]

            tracker["ORGS_COUNT"].total = len(orgs)

            # DUMP CLUSTER DATA
            d = api_transformer.ts_cluster(data=ts.session_context)
            temp.dump(models.Cluster.__tablename__, data=d)
            this_task.final()

        tracker["ORGS_COUNT"].start()

        # LOOP THROUGH EACH ORG COLLECTING DATA
        for org in orgs:
            tracker.title = f"Fetching Data in [fg-secondary]{org['name']}[/] (Org {org['id']})"
            seen_guids: dict[types.APIObjectType, set[types.GUID]] = collections.defaultdict(set)
            seen_columns: list[list[types.GUID]] = []
            seen_group_guids: set[types.GUID] = set()

            with tracker["TS_ORG"] as this_task:
                if not ts.session_context.thoughtspot.is_orgs_enabled:
                    _ = [{"id": 0, "name": "ThoughtSpot", "description": "Your cluster is not orgs enabled."}]
                else:
                    ts.config.thoughtspot.default_org = org["id"]
                    ts.login()

                    c = ts.api.orgs_search(org_id=org["id"])
                    r = utils.run_sync(c)
                    _ = r.json()

                # DUMP ORG DATA
                d = api_transformer.ts_org(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.Org.__tablename__, data=d)

            with tracker["TS_USER"] as this_task:
                c = workflows.paginator(ts.api.users_search, record_size=150_000, timeout=60 * 15)
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

            with tracker["TS_GROUP"] as this_task:
                c = workflows.paginator(ts.api.groups_search, record_size=150_000, timeout=60 * 15)
                _ = utils.run_sync(c)

                # DUMP GROUP DATA
                d = api_transformer.ts_group(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.Group.__tablename__, data=d)

                # TODO: REMOVE AFTER 10.3.0 n-1
                seen_group_guids.update([group["group_guid"] for group in d])

                # DUMP GROUP->GROUP_MEMBERSHIP DATA
                d = api_transformer.ts_group_membership(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.GroupMembership.__tablename__, data=d)

            with tracker["TS_PRIVILEGE"] as this_task:
                # TODO: ROLE->PRIVILEGE DATA.
                # TODO: GROUP->ROLE DATA.

                # DUMP GROUP->PRIVILEGE DATA
                d = api_transformer.ts_group_privilege(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.GroupPrivilege.__tablename__, data=d)

            with tracker["TS_TAG"] as this_task:
                c = ts.api.tags_search()
                r = utils.run_sync(c)
                _ = r.json()

                # DUMP TAG DATA
                d = api_transformer.ts_tag(data=_, cluster=CLUSTER_UUID, current_org=org["id"])
                temp.dump(models.Tag.__tablename__, data=d)

            with tracker["TS_METADATA"] as this_task:
                c = workflows.metadata.fetch_all(object_types=["CONNECTION", "LOGICAL_TABLE", "LIVEBOARD", "ANSWER"], http=ts.api)  # noqa: E501
                _ = utils.run_sync(c)

                # COLLECT GUIDS FOR LATER ON.. THIS WILL BE MORE EFFICIENT THAN metadata.fetch_all MULTIPLE TIMES.
                for metadata in _:
                    if is_in_current_org(metadata, current_org=org["id"]):
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

            with tracker["TS_COLUMN"] as this_task:
                g = {"LOGICAL_TABLE": seen_guids["LOGICAL_TABLE"]}
                c = workflows.metadata.fetch(typed_guids=g, include_details=True, http=ts.api)
                _ = utils.run_sync(c)

                # COLLECT GUIDS FOR LATER ON.. THIS WILL BE MORE EFFICIENT THAN metadata.fetch_all MULTIPLE TIMES.
                for metadata in _:
                    if is_in_current_org(metadata, current_org=org["id"]):
                        seen_guids["CONNECTION"].add(metadata["metadata_detail"]["dataSourceId"])
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

            with tracker["TS_DEPENDENT"] as this_task:
                g = {"LOGICAL_COLUMN": seen_columns}
                c = workflows.metadata.fetch(typed_guids=g, include_dependent_objects=True, dependent_objects_record_size=-1, http=ts.api)  # noqa: E501
                _ = utils.run_sync(c)

                # DUMP DEPENDENT_OBJECT DATA
                d = api_transformer.ts_metadata_dependent(data=_, cluster=CLUSTER_UUID)
                temp.dump(models.DependentObject.__tablename__, data=d)

            with tracker["TS_ACCESS"] as this_task:
                COMPAT_TS_VERSION = ts.session_context.thoughtspot.version
                COMPAT_GUIDS = seen_group_guids

                if include_column_access:
                    seen_guids["LOGICAL_COLUMN"] = seen_columns

                c = workflows.metadata.permissions(typed_guids=seen_guids, compat_ts_version=COMPAT_TS_VERSION, http=ts.api)  # noqa: E501
                _ = utils.run_sync(c)

                # DUMP COLUMN_SYNONYM DATA
                d = api_transformer.ts_metadata_permissions(data=_, compat_ts_version=COMPAT_TS_VERSION, compat_all_group_guids=COMPAT_GUIDS, cluster=CLUSTER_UUID)  # noqa: E501
                temp.dump(models.SharingAccess.__tablename__, data=d)

            # INCREASE THE PROGRESS BAR SINCE WE'RE DONE WITH THIS ORG
            tracker["ORGS_COUNT"].advance(step=1)
            # utils.run_sync(ts.api.cache.clear())

        tracker["ORGS_COUNT"].stop()

        with tracker["DUMP_DATA"]:
            # WRITE ALL THE COMBINED DATA TO THE TARGET SYNCER
            is_syncer_initialized_as_db_truncate = syncer.is_database_syncer and syncer.load_strategy == "TRUNCATE"

            for model in models.METADATA_MODELS:
                for idx, rows in enumerate(temp.read_stream(tablename=model.__tablename__, batch=1_000_000), start=1):
                    if is_syncer_initialized_as_db_truncate:
                        syncer.load_strategy = "TRUNCATE" if idx == 1 else "APPEND"

                    syncer.dump(model.__tablename__, data=[model.validated_init(**row).model_dump() for row in rows])

    return 0
