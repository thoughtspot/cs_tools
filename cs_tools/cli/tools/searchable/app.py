from __future__ import annotations

import datetime as dt
import json
import logging
import pathlib

from rich.live import Live
from thoughtspot_tml import Table
from thoughtspot_tml.utils import determine_tml_type
import httpx
import typer

from cs_tools import _compat
from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.layout import LiveTasks
from cs_tools.cli.types import SyncerProtocolType, TZAwareDateTimeType
from cs_tools.cli.ux import CSToolsApp, rich_console
from cs_tools.sync.sqlite.syncer import SQLite
from cs_tools.types import GUID, TMLImportPolicy

from . import layout, models, transform

log = logging.getLogger(__name__)


app = CSToolsApp(help="""Explore your ThoughtSpot metadata, in ThoughtSpot!""")


class FriendlyWindowEnd(_compat.StrEnum):
    NOW = "NOW"
    TODAY_START_UTC = "TODAY_START_UTC"
    TODAY_START_LOCAL = "TODAY_START_LOCAL"


@app.command(dependencies=[thoughtspot])
def deploy(
    ctx: typer.Context,
    connection_guid: GUID = typer.Option(
        ...,
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
):
    """
    Deploy the Searchable SpotApp.
    """
    ts = ctx.obj.thoughtspot

    if ts.session_context.thoughtspot.is_orgs_enabled and org_override is not None:
        ts.org.switch(org=org_override)

    tasks = [
        ("connection_details", "Getting details for data source"),
        ("customize_spotapp", "Customizing [b blue]Searchable Worksheets[/] to your environment"),
        ("deploy_spotapp", "Deploying the SpotApp to ThoughtSpot"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:
        with tasks["connection_details"] as this_task:
            connection_name: str = None
            dialect: str = None

            if connection_guid.lower() == "falcon":
                dialect = "FALCON"
                this_task.skip()

            else:
                try:
                    info = ts.metadata.fetch_header_and_extras(metadata_type="DATA_SOURCE", guids=[connection_guid])
                except (KeyError, IndexError):
                    log.error(f"Could not find a connection with guid {connection_guid}")
                    raise typer.Exit(1) from None

                connection_name = info[0]["header"]["name"]
                dialect = info[0]["type"]

        with tasks["customize_spotapp"]:
            here = pathlib.Path(__file__).parent
            tmls = []

            # Care for UPPERCASE or lowercase identity convention in dialects
            to_translate = str.upper if "SNOWFLAKE" in dialect else str.lower
            is_falcon_db = "FALCON" in dialect

            for file in here.glob("**/*.tml"):
                tml_cls = determine_tml_type(path=file)
                tml = tml_cls.load(file)

                if isinstance(tml, Table):
                    # Enforce ThoughtSpot Metadata to be in UPPERCASE
                    tml.table.name = tml.table.name.upper()

                    # External database object name , this has to be specific.
                    tml.table.db = database
                    tml.table.schema = schema
                    tml.table.db_table = to_translate(tml.table.db_table)

                    for column in tml.table.columns:
                        column.db_column_name = to_translate(column.db_column_name)

                    # Set the connection attribution if we're hitting an external database
                    tml.table.connection.name = connection_name if not is_falcon_db else None
                    tml.table.connection.fqn = connection_guid if not is_falcon_db else None

                # fmt: off
                # No need to replicate TS_BI_SERVER in Falcon, we'll use a Sage View instead.
                falcon_and_table =     is_falcon_db and "TS_BI_SERVER.table.tml" in file.name
                embrace_and_view = not is_falcon_db and "TS_BI_SERVER.view.tml"  in file.name
                # fmt: on

                if falcon_and_table or embrace_and_view:
                    continue

                if is_falcon_db and "TS_BI_SERVER.view.tml" in file.name:
                    tml.view.formulas[-1].expr = f"'{ts.session_context.thoughtspot.cluster_id}'"

                tmls.append(tml)

                if export is not None:
                    tml.dump(export.joinpath(file.name))

        with tasks["deploy_spotapp"] as this_task:
            if export is not None:
                this_task.skip()
                raise typer.Exit(0)

            api_responses = ts.tml.to_import(tmls, policy=TMLImportPolicy.partial)

            for r in api_responses:
                divider = "[dim bold white]>>[/]"

                if r.is_success:
                    logger = log.info
                    info = f"{r.guid} {r.metadata_object_type}"
                else:
                    logger = log.warn if r.status_code == "WARNING" else log.error
                    message = "\n   ".join(r.error_messages)
                    info = f"import log..\n   {message}"

                logger(f"{divider} [b blue]{r.name}[/] {divider} {info}")


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
    window_end: FriendlyWindowEnd = typer.Option(FriendlyWindowEnd.NOW, help="how to track events through time"),
):
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

    # THOUGHTSPOT API SEEMS TO HAVE ISSUES WITH TIMEZONES AND CAUSES DUPLICATION OF DATA
    everseen = set()

    renamed = []

    for days_to_fetch in range(last_k_days):
        utc_end = utc_terminal_end - dt.timedelta(days=days_to_fetch)
        utc_start = utc_terminal_end - dt.timedelta(days=days_to_fetch + 1)

        r = ts.api.v2.logs_fetch(log_type="SECURITY_AUDIT", utc_start=utc_start, utc_end=utc_end)

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            log.error(e.response.json())
            continue

        rows = r.json()

        if not rows:
            log.info(f"Found no data for [NOW - {days_to_fetch} DAYS] ({utc_start.date()} -> {utc_end.date()})")
            continue

        for row in rows:
            data = json.loads(row["log"])

            # THOUGHTSPOT API SEEMS TO HAVE ISSUES WITH TIMEZONES AND CAUSES DUPLICATION OF DATA
            if f"{ts.session_context.thoughtspot.cluster_id}-{data['id']}" in everseen:
                continue

            everseen.add(f"{ts.session_context.thoughtspot.cluster_id}-{data['id']}")

            renamed.append(
                models.AuditLogs.validated_init(
                    **{
                        "cluster_guid": ts.session_context.thoughtspot.cluster_id,
                        "org_id": data["orgId"],
                        "sk_dummy": f"{ts.session_context.thoughtspot.cluster_id}-{data['id']}",
                        "timestamp": row["date"],
                        "log_type": data["type"],
                        "user_guid": data["userGUID"],
                        "description": data["desc"],
                        "details": json.dumps(data["data"]),
                    }
                ).model_dump()
            )

    # CLUSTER BY --> TIMESTAMP .. everything else is irrelevant after TS.
    renamed.sort(key=lambda r: (r["timestamp"], r["sk_dummy"]))

    syncer.dump("ts_audit_logs", data=renamed)


@app.command(dependencies=[thoughtspot])
def bi_server(
    ctx: typer.Context,
    syncer: DSyncer = typer.Option(
        ...,
        click_type=SyncerProtocolType(models=models.BISERVER_MODELS),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    org_override: str = typer.Option(None, "--org", help="the org to fetch history from"),
    compact: bool = typer.Option(True, "--compact / --full", help="if compact, exclude NULL and INVALID user actions"),
    from_date: dt.datetime = typer.Option(
        None,
        click_type=TZAwareDateTimeType(),
        metavar="YYYY-MM-DD",
        help="inclusive lower bound of rows to select from TS: BI Server",
    ),
    to_date: dt.datetime = typer.Option(
        None,
        click_type=TZAwareDateTimeType(),
        metavar="YYYY-MM-DD",
        help="inclusive upper bound of rows to select from TS: BI Server",
    ),
):
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
        rich_console.print()
        raise typer.Abort()

    # DEV NOTE: @boonhapus
    # As of 9.10.0.cl , TS: BI Server only resides in the Primary Org(0), so switch to it
    if ts.session_context.thoughtspot.is_orgs_enabled:
        ts.org.switch(org=0)

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

    tasks = [
        ("gather_search", "Collecting data from [b blue]TS: BI Server"),
        ("syncer_dump", f"Writing rows to [b blue]{syncer.name}"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:
        with tasks["gather_search"]:
            data = ts.search(SEARCH_TOKENS, worksheet="TS: BI Server")

            # THOUGHTSPOT API SEEMS TO HAVE ISSUES WITH TIMEZONES AND CAUSES DUPLICATION OF DATA
            data = [dict(t) for t in {tuple(sorted(d.items())) for d in data}]

            # CLUSTER BY --> TIMESTAMP .. everything else is irrelevant after TS.
            data.sort(key=lambda r: (r["Timestamp"].replace(tzinfo=dt.timezone.utc), r["Incident Id"], r["Viz Id"]))

            renamed = []
            curr_date, sk_idx = None, 0

            for row in data:
                row_date = row["Timestamp"].replace(tzinfo=dt.timezone.utc).date()

                # reset the surrogate key every day
                if curr_date != row_date:
                    curr_date = row_date
                    sk_idx = 0

                sk_idx += 1

                renamed.append(
                    models.BIServer.validated_init(
                        **{
                            "cluster_guid": ts.session_context.thoughtspot.cluster_id,
                            "sk_dummy": f"{ts.session_context.thoughtspot.cluster_id}-{row_date}-{sk_idx}",
                            "org_id": row.get("Org Id", 0),
                            "incident_id": row["Incident Id"],
                            "timestamp": row["Timestamp"],
                            "url": row["URL"],
                            "http_response_code": row["HTTP Response Code"],
                            "browser_type": row["Browser Type"],
                            "browser_version": row["Browser Version"],
                            "client_type": row["Client Type"],
                            "client_id": row["Client Id"],
                            "answer_book_guid": row["Answer Book GUID"],
                            "viz_id": row["Viz Id"],
                            "user_id": row["User Id"],
                            "user_action": row["User Action"],
                            "query_text": row["Query Text"],
                            "response_size": row["Total Response Size"],
                            "latency_us": row["Total Latency (us)"],
                            "impressions": row["Total Impressions"],
                        }
                    ).model_dump()
                )

        with tasks["syncer_dump"]:
            syncer.dump("ts_bi_server", data=renamed)


@app.command("gather", dependencies=[thoughtspot], hidden=True)
def _gather(
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
):
    # Here for backwards compatability.
    command = typer.main.get_command(app).get_command(ctx, "metadata")
    ctx.forward(command)


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
):
    """
    Extract metadata from your ThoughtSpot platform.

    \b
    See the full data model extract at the link below:
      [url]https://thoughtspot.github.io/cs_tools/cs-tools/searchable[/]
    """
    ts = ctx.obj.thoughtspot

    if ts.session_context.thoughtspot.is_orgs_enabled:
        info = ts.api.v1.session_orgs_read().json().get("orgs", [])
        orgs = [i["orgId"] for i in info] if org_override is None else [ts.org.guid_for(org_override)]
    else:
        orgs = ["ThoughtSpot"]

    if not ts.session_context.user.is_admin:
        log.warning("Searchable is meant to be run from an Admin-level context, your results may vary..")

    table = layout.Table(data=[[str(org)] + [":popcorn:"] * 8 for org in orgs])
    temp_sync = SQLite(
        database_path=ts.config.temp_dir / "temp-data.db", models=models.METADATA_MODELS, load_strategy="UPSERT"
    )

    # Silence the intermediate logger.
    logging.getLogger("cs_tools.sync.sqlite.syncer").setLevel(logging.CRITICAL)

    with Live(table, console=rich_console, auto_refresh=1):
        temp_sync.dump(models.Cluster.__tablename__, data=transform.to_cluster(ts.session_context))
        cluster_uuid = ts.session_context.thoughtspot.cluster_id

        for row, org_id in zip(table.data, orgs):
            if ts.session_context.thoughtspot.is_orgs_enabled:
                ts.org.switch(org_id)
                row[1] = ":fire:"

                # org info
                r = ts.api.v1.org_read(org_id=org_id)
                temp_sync.dump(models.Org.__tablename__, data=transform.to_org(r.json(), cluster=cluster_uuid))

                # org_membership
                r = ts.api.v1.user_read()
                members = {tuple(m.values()) for m in temp_sync.load(models.OrgMembership.__tablename__)}
                transformed = transform.to_org_membership(r.json(), cluster=cluster_uuid, ever_seen=members)
                temp_sync.dump(models.OrgMembership.__tablename__, data=transformed)
                row[1] = ":file_folder:"
            else:
                default_org = {"orgId": 0, "orgName": "ThoughtSpot", "description": "Your cluster is not orgs enabled."}
                temp_sync.dump(models.Org.__tablename__, data=transform.to_org(default_org, cluster=cluster_uuid))
                row[1] = ""

            row[2] = ":fire:"
            # user
            # group_membership
            r = ts.api.v1.user_read()
            members = {m["user_guid"] for m in temp_sync.load(models.User.__tablename__)}
            temp_sync.dump(
                models.User.__tablename__, data=transform.to_user(r.json(), cluster=cluster_uuid, ever_seen=members)
            )
            temp_sync.dump(
                models.GroupMembership.__tablename__, data=transform.to_group_membership(r.json(), cluster=cluster_uuid)
            )
            row[2] = ":file_folder:"

            row[3] = ":fire:"
            # group
            # group_privilege
            # group_membership
            r = ts.api.v1.group_read()
            temp_sync.dump(models.Group.__tablename__, data=transform.to_group(r.json(), cluster=cluster_uuid))
            temp_sync.dump(
                models.GroupPrivilege.__tablename__, data=transform.to_group_privilege(r.json(), cluster=cluster_uuid)
            )
            temp_sync.dump(
                models.GroupMembership.__tablename__, data=transform.to_group_membership(r.json(), cluster=cluster_uuid)
            )
            row[3] = ":file_folder:"

            row[4] = ":fire:"
            # tags
            r = ts.tag.all()
            temp_sync.dump(models.Tag.__tablename__, data=transform.to_tag(r, cluster=cluster_uuid))
            row[4] = ":file_folder:"

            row[5] = ":fire:"
            # metadata
            content = [
                *ts.logical_table.all(exclude_system_content=False, include_data_source=True, raise_on_error=False),
                *ts.answer.all(exclude_system_content=False, raise_on_error=False),
                *ts.liveboard.all(exclude_system_content=False, raise_on_error=False),
            ]

            members = {
                (m["cluster_guid"], m["org_id"], m["object_guid"])
                for m in temp_sync.load(models.MetadataObject.__tablename__)
            }
            temp_sync.dump(
                models.DataSource.__tablename__, data=transform.to_data_source(content, cluster=cluster_uuid)
            )
            temp_sync.dump(
                models.MetadataObject.__tablename__,
                data=transform.to_metadata_object(content, cluster=cluster_uuid, ever_seen=members),
            )
            temp_sync.dump(
                models.TaggedObject.__tablename__, data=transform.to_tagged_object(content, cluster=cluster_uuid)
            )
            row[5] = ":file_folder:"

            # columns
            # synonyms
            row[6] = ":fire:"
            guids = [obj["id"] for obj in content if obj["metadata_type"] == "LOGICAL_TABLE"]
            r = ts.logical_table.columns(guids)
            temp_sync.dump(
                models.MetadataColumn.__tablename__, data=transform.to_metadata_column(r, cluster=cluster_uuid)
            )
            temp_sync.dump(
                models.ColumnSynonym.__tablename__, data=transform.to_column_synonym(r, cluster=cluster_uuid)
            )
            row[6] = ":file_folder:"

            # dependents
            row[7] = ":fire:"
            r = ts.metadata.dependents([column["column_guid"] for column in r], for_columns=True)
            temp_sync.dump(
                models.DependentObject.__tablename__, data=transform.to_dependent_object(r, cluster=cluster_uuid)
            )
            row[7] = ":file_folder:"

            # access_controls
            row[8] = ":fire:"
            types = ["QUESTION_ANSWER_BOOK", "PINBOARD_ANSWER_BOOK", "LOGICAL_TABLE", "DATA_SOURCE"]

            if include_column_access:
                types.append("LOGICAL_COLUMN")

            # NOTE:
            #    In the case the ThoughtSpot cluster has a high number of users, the
            #    column access block will take an incredibly long amount of time to
            #    complete. We can probably find a better algorithm.
            #
            for metadata_type in types:
                guids = [obj["id"] for obj in content if obj["metadata_type"] == metadata_type]
                r = ts.metadata.permissions(guids, metadata_type=metadata_type)
                temp_sync.dump(
                    models.SharingAccess.__tablename__, data=transform.to_sharing_access(r, cluster=cluster_uuid)
                )

            row[8] = ":file_folder:"

            # GO TO NEXT ORG BATCH -->

        # WRITE ALL THE COMBINED DATA TO THE TARGET SYNCER
        is_syncer_initialized_as_db_truncate = syncer.is_database_syncer and syncer.load_strategy == "TRUNCATE"

        for model in models.METADATA_MODELS:
            for idx, rows in enumerate(temp_sync.read_stream(tablename=model.__tablename__, batch=1_000_000), start=1):
                if is_syncer_initialized_as_db_truncate:
                    syncer.load_strategy = "TRUNCATE" if idx == 1 else "APPEND"

                syncer.dump(model.__tablename__, data=[model.validated_init(**row).model_dump() for row in rows])
