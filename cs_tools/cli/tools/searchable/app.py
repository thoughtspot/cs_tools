import datetime as dt
import logging

from typer import Argument as A_, Option as O_  # noqa
import typer

from cs_tools.cli.tools.common import setup_thoughtspot
from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT
from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand, SyncerProtocolType

from . import transform


log = logging.getLogger(__name__)


app = typer.Typer(
    help="""
    Explore your ThoughtSpot metadata, in ThoughtSpot!
    """,
    cls=CSToolsGroup
)


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def bi_server(
    ctx: typer.Context,
    # Note:
    # really this is a SyncerProtocolType type,
    # but typer does not yet support click.ParamType,
    # so we can fake it with a callback :~)
    export: str = A_(
        ...,
        help='protocol and path for options to pass to the syncer',
        metavar='protocol://DEFINITION.toml',
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    ),
    compact: bool = O_(True, '--compact / --full', help='if compact, exclude NULL and INVALID user actions'),
    from_date: dt.datetime = O_(None, metavar='YYYY-MM-DD', help='lower bound of rows to select from TS: BI Server'),
    to_date: dt.datetime = O_(None, metavar='YYYY-MM-DD', help='upper bound of rows to select from TS: BI Server'),
    include_today: bool = O_(False, '--include-today', help='if set, pull partial day data', show_default=False),
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
    SEARCH_TOKENS = (
        "[incident id] [timestamp].'detailed' [url] [http response code] "
        "[browser type] [browser version] [client type] [client id] [answer book guid] "
        "[viz id] [user id] [user action] [query text] [response size] [latency (us)] "
        "[database latency (us)] [impressions]"
        + ("" if compact else " [user action] != {null} 'invalid'")
        + ("" if from_date is None else f" [timestamp] >= '{from_date.date()}'")
        + ("" if to_date is None else f" [timestamp] <= '{to_date.date()}'")
        + ("" if include_today else " [timestamp] != 'today'")
    )

    ts = ctx.obj.thoughtspot

    with console.status('[bold green]getting TS: BI Server data..'):
        data = ts.search(SEARCH_TOKENS, worksheet='TS: BI Server')

    with console.status(f'[bold green]writing TS: BI Server to {export.name}..'):
        seed = dt.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        renamed = [
            {
                'sk_dummy': f'{seed}-{idx}',
                'incident_id': _['Incident Id'],
                'timestamp': dt.datetime.fromtimestamp(_['Timestamp'] or 0),
                'url': _['URL'],
                'http_response_code': _['HTTP Response Code'],
                'browser_type': _['Browser Type'],
                'browser_version': _['Browser Version'],
                'client_type': _['Client Type'],
                'client_id': _['Client Id'],
                'answer_book_guid': _['Answer Book GUID'],
                'viz_id': _['Viz Id'],
                'user_id': _['User Id'],
                'user_action': _['User Action'],
                'query_text': _['Query Text'],
                'response_size': _['Total Response Size'],
                'latency_us': _['Total Latency (us)'],
                'impressions': _['Total Impressions']
            }
            for idx, _ in enumerate(data)
        ]

        export.dump('ts_bi_server', data=renamed)


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def gather(
    ctx: typer.Context,
    # Note:
    # really this is a SyncerProtocolType type,
    # but typer does not yet support click.ParamType,
    # so we can fake it with a callback :~)
    export: str = A_(
        ...,
        help='protocol and path for options to pass to the syncer',
        metavar='protocol://DEFINITION.toml',
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    ),
):
    """
    Extract metadata from your ThoughtSpot platform.

    See the full data model extract at the link below:
      https://thoughtspot.github.io/cs_tools/cs-tools/searchable
    """
    ts = ctx.obj.thoughtspot

    with console.status('[bold green]getting groups..'):
        r = ts.api.request('GET', 'group', privacy='public')

    with console.status(f'[bold green]writing groups to {export.name}..'):
        xref = transform.to_principal_association(r.json())
        data = transform.to_group(r.json())
        export.dump('ts_group', data=data)

        data = transform.to_group_privilege(r.json())
        export.dump('ts_group_privilege', data=data)

    with console.status('[bold green]getting users..'):
        r = ts.api.request('GET', 'user', privacy='public')

    with console.status(f'[bold green]writing users to {export.name}..'):
        data = transform.to_user(r.json())
        export.dump('ts_user', data=data)

        data = [*xref, *transform.to_principal_association(r.json())]
        export.dump('ts_xref_principal', data=data)
        del xref

    with console.status('[bold green]getting tags..'):
        r = ts.tag.all()

    with console.status(f'[bold green]writing tags to {export.name}..'):
        data = transform.to_tag(r)
        export.dump('ts_tag', data=data)

    with console.status('[bold green]getting metadata..'):
        content = ts.metadata.all(exclude_system_content=False)

    with console.status(f'[bold green]writing metadata to {export.name}..'):
        data = transform.to_metadata_object(content)
        export.dump('ts_metadata_object', data=data)

        data = transform.to_tagged_object(content)
        export.dump('ts_tagged_object', data=data)

    with console.status('[bold green]getting columns..'):
        guids = [_['id'] for _ in content if not _['type'].endswith('BOOK')]
        data = ts.metadata.columns(guids, include_hidden=True)

    with console.status(f'[bold green]writing columns to {export.name}..'):
        data = transform.to_metadata_column(data)
        export.dump('ts_metadata_column', data=data)

    with console.status('[bold green]getting dependents..'):
        types = ('LOGICAL_COLUMN', 'FORMULA', 'CALENDAR_TABLE')
        guids = [_['column_guid'] for _ in data]
        r = ts.metadata.dependents(guids, for_columns=True)

    with console.status(f'[bold green]writing dependents to {export.name}..'):
        data = transform.to_dependent_object(r)
        export.dump('ts_dependent_object', data=data)

    with console.status('[bold green]getting sharing access..'):
        types = {
            'QUESTION_ANSWER_BOOK': ('QUESTION_ANSWER_BOOK', ),
            'PINBOARD_ANSWER_BOOK': ('PINBOARD_ANSWER_BOOK', ),
            'LOGICAL_TABLE': (
                'ONE_TO_ONE_LOGICAL', 'USER_DEFINED', 'WORKSHEET', 'AGGR_WORKSHEET',
                'MATERIALIZED_VIEW', 'SQL_VIEW', 'LOGICAL_TABLE'
            ),
            'LOGICAL_COLUMN': ('FORMULA', 'CALENDAR_TABLE', 'LOGICAL_COLUMN')
        }

        data = []

        for type_, subtypes in types.items():
            guids = [_['id'] for _ in content if _['type'] in subtypes]
            r = ts.metadata.permissions(guids, type=type_)
            data.extend(transform.to_sharing_access(r))

            # DEV NOTE:
            #   this does not exist in TS apis as of 2022/03, the call below only
            #   retrieves inherited/effective sharing access for the authenticated
            #   user
            #
            # r = ts.metadata.permissions(guids, type=type_, permission_type='EFFECTIVE')

    with console.status(f'[bold green]writing sharing access to {export.name}..'):
        export.dump('ts_sharing_access', data=data)
