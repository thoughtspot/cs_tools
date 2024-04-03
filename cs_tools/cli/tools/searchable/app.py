from __future__ import annotations

import datetime as dt
import logging
import pathlib

from rich.live import Live
from thoughtspot_tml import Table
from thoughtspot_tml.utils import determine_tml_type
import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.layout import LiveTasks
from cs_tools.cli.types import SyncerProtocolType, TZAwareDateTimeType
from cs_tools.cli.ux import CSToolsApp, rich_console
from cs_tools.sync.csv.syncer import CSV
from cs_tools.types import GUID, TMLImportPolicy

from . import layout, models, transform

log = logging.getLogger(__name__)


app = CSToolsApp(help="""Explore your ThoughtSpot metadata, in ThoughtSpot!""")


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

    tasks = [
        ("connection_details", "Getting details for data source"),
        ("customize_spotapp", "Customizing [b blue]Searchable Worksheets[/] to your environment"),
        ("deploy_spotapp", "Deploying the SpotApp to ThoughtSpot"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:
        with tasks["connection_details"] as this_task:
            connection_guid: str = None
            connection_name: str = None
            dialect: str = None

            if connection_guid == "falcon":
                dialect = "FALCON"
                this_task.skip()

            else:
                try:
                    info = ts.metadata.fetch_data_source_info(connection_guid)
                except AttributeError:
                    log.error(f"Could not find a connection with guid {connection_guid}")
                    raise typer.Exit(1) from None

                connection_guid = info["header"]["id"]
                connection_name = info["header"]["name"]
                dialect = info["header"]["type"]

        # Care for UPPERCASE or lowercase identity convention in dialects
        should_upper = "SNOWFLAKE" in dialect

        with tasks["customize_spotapp"]:
            here = pathlib.Path(__file__).parent
            tmls = []

            for file in here.glob("**/*.tml"):
                tml_cls = determine_tml_type(path=file)
                tml = tml_cls.load(file)

                if isinstance(tml, Table):
                    tml.table.db = database
                    tml.table.schema = schema
                    tml.table.db_table = tml.table.db_table.upper() if should_upper else tml.table.db_table.lower()
                    tml.table.name = tml.table.name.upper() if should_upper else tml.table.name.lower()

                    if dialect != "FALCON":
                        tml.table.connection.name = connection_name
                        tml.table.connection.fqn = connection_guid

                # No need to replicate TS_BI_SERVER in Falcon, we'll use a Sage View instead.
                if dialect == "FALCON" and "TS_BI_SERVER.table.tml" in file.name:
                    continue

                if dialect == "FALCON" and "TS_BI_SERVER.view.tml" in file.name:
                    tml.view.formulas[-1].expr = f"'{ts.session_context.thoughtspot.cluster_id}'"

                tmls.append(tml)

                if export is not None:
                    tml.dump(export.joinpath(file.name))

        with tasks["deploy_spotapp"] as this_task:
            if export is not None:
                this_task.skip()
                raise typer.Exit(0)

            responses = ts.tml.to_import(tmls, policy=TMLImportPolicy.partial)

            centered_table = layout.build_table()

            for row in responses:
                centered_table.renderable.add_row(
                    ":cross_mark:" if row.is_error else ":white_heavy_check_mark:",
                    row.tml_type_name,
                    row.guid or "{null}",
                    row.name,
                    "; ".join(row.error_messages) or "{null}",
                )

            rich_console.print(centered_table)


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

    # DEV NOTE: @boonhapus
    # As of 9.10.0.cl , TS: BI Server only resides in the Primary Org(0), so switch to it

    if ts.session_context.thoughtspot.is_orgs_enabled:
        ts.org.switch(org=0)

    elif org_override is not None:
        org_override = None

    SEARCH_DATA_DATE_FMT = "%m/%d/%Y"
    SEARCH_TOKENS = (
        "[org id] [incident id] [timestamp].'detailed' [url] [http response code] "
        "[browser type] [browser version] [client type] [client id] [answer book guid] "
        "[viz id] [user id] [user action] [query text] [response size] [latency (us)] "
        "[database latency (us)] [impressions] [timestamp] != 'today'"
        + "[incident id] != [incident id].{null}"
        + ("" if not compact else " [User Action] != [User Action].invalid [User Action].{null}")
        + ("" if from_date is None else f" [timestamp] >= '{from_date.strftime(SEARCH_DATA_DATE_FMT)}'")
        + ("" if to_date is None else f" [timestamp] <= '{to_date.strftime(SEARCH_DATA_DATE_FMT)}'")
        + ("" if org_override is None else f"[org id] = {ts.org.guid_for(org_override)}")
    )

    tasks = [
        ("gather_search", "Collecting data from [b blue]TS: BI Server"),
        ("syncer_dump", f"Writing rows to [b blue]{syncer.name}"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:
        with tasks["gather_search"]:
            data = ts.search(SEARCH_TOKENS, worksheet="TS: BI Server")

            # SEARCH DATA API SEEMS TO HATE ISSUES WITH TIMEZONES AND CAUSES DUPLICATION OF DATA
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
                            "org_id": row.get("Org ID", 0),
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
    temp_sync = CSV(directory=ts.config.temp_dir, empty_as_null=True, save_strategy="APPEND")

    # Orgs have the potential for having limited data, let's be less noisy.
    logger = logging.getLogger("cs_tools.sync.csv.syncer")
    logger.setLevel("ERROR")

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
                models.DataSource.__tablename__,
                data=transform.to_data_source(content, cluster=cluster_uuid),
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
            r = ts.logical_table.columns(guids, include_hidden=True)
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
            types = {
                "QUESTION_ANSWER_BOOK": ("QUESTION_ANSWER_BOOK",),
                "PINBOARD_ANSWER_BOOK": ("PINBOARD_ANSWER_BOOK",),
                "LOGICAL_TABLE": (
                    "ONE_TO_ONE_LOGICAL",
                    "USER_DEFINED",
                    "WORKSHEET",
                    "AGGR_WORKSHEET",
                    "MATERIALIZED_VIEW",
                    "SQL_VIEW",
                    "LOGICAL_TABLE",
                ),
            }

            if include_column_access:
                types["LOGICAL_COLUMN"] = ("FORMULA", "CALENDAR_TABLE", "LOGICAL_COLUMN")

            # NOTE:
            #    In the case the ThoughtSpot cluster has a high number of users, the
            #    column access block will take an incredibly long amount of time to
            #    complete. We can probably find a better algorithm.
            #
            for metadata_type, metadata_subtypes in types.items():
                guids = [obj["id"] for obj in content if obj["metadata_type"] in metadata_subtypes]
                r = ts.metadata.permissions(guids, type=metadata_type)
                temp_sync.dump(
                    models.SharingAccess.__tablename__, data=transform.to_sharing_access(r, cluster=cluster_uuid)
                )

            row[8] = ":file_folder:"

            # GO TO NEXT ORG BATCH -->

        # RESTORE CSV logger.level
        logger.setLevel("DEBUG")

        # WRITE ALL THE COMBINED DATA TO THE TARGET SYNCER
        for model in models.METADATA_MODELS:
            for rows in temp_sync.read_stream(filename=model.__tablename__, batch=1_000_000):
                syncer.dump(model.__tablename__, data=[model.validated_init(**row).model_dump() for row in rows])
