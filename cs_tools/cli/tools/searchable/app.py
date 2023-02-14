import datetime as dt
from typing import List
import logging
import pathlib

import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.types import TZAwareDateTimeType, SyncerProtocolType
from cs_tools.cli.ux import rich_console
from cs_tools.cli.ux import CSToolsArgument as Arg
from cs_tools.cli.ux import CSToolsOption as Opt
from cs_tools.cli.ux import CSToolsApp
from cs_tools.types import GUID
from cs_tools.cli.dependencies.syncer import DSyncer
from cs_tools.cli.layout import LiveTasks
from cs_tools.types import TMLImportPolicy
from thoughtspot_tml.utils import determine_tml_type
from thoughtspot_tml import Table

from ._version import __version__
from . import transform
from . import layout
from . import models

log = logging.getLogger(__name__)


app = CSToolsApp(help="""Explore your ThoughtSpot metadata, in ThoughtSpot!""")


@app.command(dependencies=[thoughtspot])
def deploy(
    ctx: typer.Context,
    connection_guid: GUID = Opt(
        ...,
        help=(
            "if Falcon, use [b blue]falcon[/], otherwise to find your connection guid, go to Data > Connections > your "
            "connection, and copying the ID in the URL"
        )
    ),
    database: str = Opt(
        ...,
        help=(
            "if Falcon, database is likely [b blue]cs_tools[/], otherwise it is the name of the database which holds "
            "CS Tools Searchable data"
        )
    ),
    schema: str = Opt(
        ...,
        help=(
            "if Falcon, schema is likely [b blue]falcon_default_schema[/], otherwise it is the name of the database "
            "which holds name of the schema which holds CS Tools Searchable data"
        )
    ),
):
    """
    Deploy the Searchable SpotApp.
    """
    ts = ctx.obj.thoughtspot
    is_falcon = connection_guid == "falcon"
    
    tasks = [
        ("connection_details", f"Getting details for connection {'' if is_falcon else connection_guid}"),
        ("customize_spotapp", "Customizing [b blue]Searchable Worksheets[/] to your environment"),
        ("deploy_spotapp", "Deploying the SpotApp to ThoughtSpot"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:

        with tasks["connection_details"] as this_task:
            if is_falcon:
                this_task.skip()
            else:
                r = ts.api.metadata_list(metadata_type="DATA_SOURCE", fetch_guids=[connection_guid])
                data = r.json()["headers"][0]
                connection_guid = data["id"]
                connection_name = data["name"]

        with tasks["customize_spotapp"]:
            here = pathlib.Path(__file__).parent
            tmls = []

            for file in here.glob("**/*.tml"):
                tml_cls = determine_tml_type(path=file)
                tml = tml_cls.load(file)
                tml.guid = None

                if isinstance(tml, Table):
                    tml.table.db = database
                    tml.table.schema = schema
                    
                    if is_falcon:
                        tml.table.connection = None
                    else:
                        tml.table.connection.name = connection_name
                        tml.table.connection.fqn = connection_guid

                tmls.append(tml)

    #     with tasks["deploy_spotapp"]:
    #         response = ts.tml.to_import(tmls, policy=TMLImportPolicy.all_or_none)

    # status_emojis = {"OK": ":white_heavy_check_mark:", "WARNING": ":pinching_hand:", "ERROR": ":cross_mark:"}
    # centered_table = layout.build_table()

    # for response in response:
    #     status = status_emojis.get(response.status_code, ":cross_mark:")
    #     guid = response.guid or "[gray]{null}"
    #     centered_table.renderable.add_row(status, response.tml_type_name, guid, response.name)

    # rich_console.print(centered_table)


@app.command(dependencies=[thoughtspot])
def bi_server(
    ctx: typer.Context,
    export: DSyncer = Opt(
        None,
        custom_type=SyncerProtocolType(models=models.BISERVER_MODELS),
        help="protocol and path for options to pass to the syncer",
        rich_help_panel="Syncer Options",
    ),
    compact: bool = Opt(True, "--compact / --full", help="if compact, exclude NULL and INVALID user actions"),
    from_date: dt.datetime = Opt(
        None,
        custom_type=TZAwareDateTimeType(),
        metavar="YYYY-MM-DD",
        help="lower bound of rows to select from TS: BI Server",
    ),
    to_date: dt.datetime = Opt(
        None,
        custom_type=TZAwareDateTimeType(),
        metavar="YYYY-MM-DD",
        help="upper bound of rows to select from TS: BI Server",
    ),
    include_today: bool = Opt(False, "--include-today", help="pull partial day data", show_default=False),
):
    """
    Extract usage statistics from your ThoughtSpot platform.

    \b
    Fields extracted from TS: BI Server
        - incident id           - timestamp detailed    - url
        - http response code    - browser type          - client type
        - client id             - answer book guid      - viz id
        - user id               - user action           - query text
        - response size         - latency (us)          - database latency (us)
        - impressions
    """
    SEARCH_DATA_DATE_FMT = "%m/%d/%Y"
    SEARCH_TOKENS = (
        "[incident id] [timestamp].'detailed' [url] [http response code] "
        "[browser type] [browser version] [client type] [client id] [answer book guid] "
        "[viz id] [user id] [user action] [query text] [response size] [latency (us)] "
        "[database latency (us)] [impressions]"
        + ("" if compact else " [user action] != {null} 'invalid'")
        + ("" if from_date is None else f" [timestamp] >= '{from_date.strftime(SEARCH_DATA_DATE_FMT)}'")
        + ("" if to_date is None else f" [timestamp] <= '{to_date.strftime(SEARCH_DATA_DATE_FMT)}'")
        + ("" if include_today else " [timestamp] != 'today'")
    )

    ts = ctx.obj.thoughtspot

    tasks = [
        ("gather_search", "Collecting data from [b blue]TS: BI Server"),
        ("syncer_dump", f"Writing rows to [b blue]{export.name}"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:

        with tasks["gather_search"]:
            data = ts.search(SEARCH_TOKENS, worksheet="TS: BI Server")
            seed = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            renamed = [
                {
                    "sk_dummy": f"{seed}-{idx}",
                    "incident_id": _["Incident Id"],
                    "timestamp": _["Timestamp"],
                    "url": _["URL"],
                    "http_response_code": _["HTTP Response Code"],
                    "browser_type": _["Browser Type"],
                    "browser_version": _["Browser Version"],
                    "client_type": _["Client Type"],
                    "client_id": _["Client Id"],
                    "answer_book_guid": _["Answer Book GUID"],
                    "viz_id": _["Viz Id"],
                    "user_id": _["User Id"],
                    "user_action": _["User Action"],
                    "query_text": _["Query Text"],
                    "response_size": _["Total Response Size"],
                    "latency_us": _["Total Latency (us)"],
                    "impressions": _["Total Impressions"],
                }
                for idx, _ in enumerate(data)
            ]

        with tasks["syncer_dump"]:
            export.dump("ts_bi_server", data=renamed)


@app.command(dependencies=[thoughtspot])
def gather(
    ctx: typer.Context,
    # tables: List[str] = Opt(None, help="table names to collect data on, can be specified multiple times"),
    export: DSyncer = Opt(
        None,
        custom_type=SyncerProtocolType(models=models.METADATA_MODELS),
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

    tasks = [
        ("gather_groups", "Collecting [b blue]Groups [white]and[/] Privileges"),
        ("syncer_dump_groups", f"Writing [b blue]Groups[/] to {export.name}"),
        ("syncer_dump_group_privileges", f"Writing [b blue]Groups Privileges[/] to {export.name}"),
        ("gather_users", "Collecting [b blue]Users"),
        ("syncer_dump_users", f"Writing [b blue]Users[/] to {export.name}"),
        ("syncer_dump_associations", f"Writing [b blue]User [white]and[/] Group Associations[/] to {export.name}"),
        ("gather_tags", "Collecting [b blue]Tags"),
        ("syncer_dump_tags", f"Writing [b blue]Tags[/] to {export.name}"),
        ("gather_metadata", "Collecting [b blue]Metadata"),
        ("syncer_dump_metadata", f"Writing [b blue]Metadata[/] to {export.name}"),
        ("gather_metadata_columns", "Collecting [b blue]Metadata Columns"),
        ("syncer_dump_metadata_columns", f"Writing [b blue]Metadata Columns[/] to {export.name}"),
        ("syncer_dump_synonyms", f"Writing [b blue]Synonyms[/] to {export.name}"),
        ("gather_dependents", "Collecting [b blue]Dependencies"),
        ("syncer_dump_dependents", f"Writing [b blue]Metadata Dependents[/] to {export.name}"),
        ("gather_access_controls", "Collecting [b blue]Sharing Access Controls"),
        ("syncer_dump_access_controls", f"Writing [b blue]Sharing Access Controls[/] to {export.name}"),
    ]

    with LiveTasks(tasks, console=rich_console) as tasks:

        with tasks["gather_groups"]:
            r = ts.api.group_read()

        with tasks["syncer_dump_groups"]:
            xref = transform.to_principal_association(r.json())
            data = transform.to_group(r.json())
            export.dump("ts_group", data=data)

        with tasks["syncer_dump_group_privileges"]:
            data = transform.to_group_privilege(r.json())
            export.dump("ts_group_privilege", data=data)

        with tasks["gather_users"]:
            r = ts.api.user_read()

        with tasks["syncer_dump_users"]:
            data = transform.to_user(r.json())
            export.dump("ts_user", data=data)

        with tasks["syncer_dump_associations"]:
            data = [*xref, *transform.to_principal_association(r.json())]
            export.dump("ts_xref_principal", data=data)
            del xref

        with tasks["gather_tags"]:
            r = ts.tag.all()

        with tasks["syncer_dump_tags"]:
            data = transform.to_tag(r)
            export.dump("ts_tag", data=data)

        with tasks["gather_metadata"]:
            content = [
                *ts.logical_table.all(exclude_system_content=False),
                *ts.answer.all(exclude_system_content=False),
                *ts.liveboard.all(exclude_system_content=False),
            ]

        with tasks["syncer_dump_metadata"]:
            data = transform.to_metadata_object(content)
            export.dump("ts_metadata_object", data=data)

            data = transform.to_tagged_object(content)
            export.dump("ts_tagged_object", data=data)

        with tasks["gather_metadata_columns"]:
            guids = [_["id"] for _ in content if not _["metadata_type"].endswith("BOOK")]
            data = ts.logical_table.columns(guids, include_hidden=True)

        with tasks["syncer_dump_metadata_columns"]:
            col_ = transform.to_metadata_column(data)
            export.dump("ts_metadata_column", data=col_)

        with tasks["syncer_dump_synonyms"]:
            syn_ = transform.to_column_synonym(data)
            export.dump("ts_column_synonym", data=syn_)

        with tasks["gather_dependents"]:
            types = ("LOGICAL_COLUMN", "FORMULA", "CALENDAR_TABLE")
            guids = [_["column_guid"] for _ in data]
            r = ts.metadata.dependents(guids, for_columns=True)

        with tasks["syncer_dump_dependents"]:
            data = transform.to_dependent_object(r)
            export.dump("ts_dependent_object", data=data)

        with tasks["gather_access_controls"]:
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
                "LOGICAL_COLUMN": ("FORMULA", "CALENDAR_TABLE", "LOGICAL_COLUMN"),
            }

            data = []

            # NOTE:
            #    In the case the ThoughtSpot cluster has a high number of users, this block
            #    will take an incredibly long amount of time to complete. We can probably
            #    find a better algorithm.
            #
            for type_, subtypes in types.items():
                guids = [_["id"] for _ in content if _["metadata_type"] in subtypes]
                r = ts.metadata.permissions(guids, type=type_)
                data.extend(transform.to_sharing_access(r))

                # DEV NOTE:
                #   this does not exist in TS apis as of 2022/03, the call below only
                #   retrieves inherited/effective sharing access for the authenticated
                #   user
                #
                # r = ts.metadata.permissions(guids, type=type_, permission_type='EFFECTIVE')

        with tasks["syncer_dump_access_controls"]:
            export.dump("ts_sharing_access", data=data)
