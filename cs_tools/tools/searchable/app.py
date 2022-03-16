import datetime as dt
import logging

from typer import Argument as A_, Option as O_  # noqa
import typer

from cs_tools.helpers.cli_ux import (
    console, frontend, CSToolsGroup, CSToolsCommand, SyncerProtocolType
)
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools.settings import TSConfig

from . import transform


log = logging.getLogger(__name__)


app = typer.Typer(
    help="""
    Explore your ThoughtSpot metadata, in ThoughtSpot!
    """,
    cls=CSToolsGroup
)
@app.command(cls=CSToolsCommand)
@frontend
def gather(
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
    include_columns: bool=O_(False, '--include-columns', help='...', show_default=False),
    **frontend_kw
):
    """
    Lorem, ipsum.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw)

    with ThoughtSpot(cfg) as ts:
        with console.status('[bold green]getting groups..[/]'):
            r = ts.api.request('GET', 'group', privacy='public')

        with console.status(f'[bold green]writing groups to {export.name}..[/]'):
            data = transform.to_group(r.json())
            export.dump('ts_group', data=data)

            data = transform.to_group_privilege(r.json())
            export.dump('ts_group_privilege', data=data)

            data = transform.to_principal_association(r.json())
            export.dump('ts_xref_principal', data=data)

        with console.status('[bold green]getting users..[/]'):
            r = ts.api.request('GET', 'user', privacy='public')

        with console.status(f'[bold green]writing users to {export.name}..[/]'):
            data = transform.to_user(r.json())
            export.dump('ts_user', data=data)

            data = transform.to_principal_association(r.json())
            export.dump('ts_xref_principal', data=data)

        with console.status('[bold green]getting tags..[/]'):
            r = ts.tag.all()

        with console.status(f'[bold green]writing tags to {export.name}..[/]'):
            data = transform.to_tag(r)
            export.dump('ts_tag', data=data)

        with console.status('[bold green]getting metadata..[/]'):
            content = ts.metadata.all(
                        include_columns=include_columns,
                        exclude_system_content=False
                    )

        with console.status(f'[bold green]writing metadata to {export.name}..[/]'):
            data = transform.to_metadata_object(content)
            export.dump('ts_metadata_object', data=data)

            data = transform.to_tagged_object(content)
            export.dump('ts_tagged_object', data=data)

        with console.status('[bold green]getting dependents..[/]'):
            types = (
                'LOGICAL_TABLE', 'ONE_TO_ONE_LOGICAL', 'USER_DEFINED', 'WORKSHEET',
                'AGGR_WORKSHEET', 'MATERIALIZED_VIEW', 'SQL_VIEW'
            )
            guids = [_['id'] for _ in content if _['type'] in types]
            r = ts.metadata.dependents(guids, for_columns=include_columns)

            if include_columns:
                types = ('LOGICAL_COLUMN', 'FORMULA', 'CALENDAR_TABLE')
                _ = ts.metadata.dependents(guids, for_columns=include_columns)
                r.extend(_)

        with console.status(f'[bold green]writing dependents to {export.name}..[/]'):
            data = transform.to_dependent_object(r)
            export.dump('ts_dependent_object', data=data)

        with console.status('[bold green]getting sharing access..[/]'):
            types = {
                'QUESTION_ANSWER_BOOK': ('QUESTION_ANSWER_BOOK', ),
                'PINBOARD_ANSWER_BOOK': ('PINBOARD_ANSWER_BOOK', ),
                'LOGICAL_TABLE': (
                    'ONE_TO_ONE_LOGICAL', 'USER_DEFINED', 'WORKSHEET', 'AGGR_WORKSHEET',
                    'MATERIALIZED_VIEW', 'SQL_VIEW', 'LOGICAL_TABLE'
                )
            }

            if include_columns:
                types['LOGICAL_COLUMN'] = ('FORMULA', 'CALENDAR_TABLE', 'LOGICAL_COLUMN')
    
            data = []

            for type_, subtypes in types.items():
                guids = [_['id'] for _ in content if _['type'] in subtypes]
                r = ts.metadata.permissions(guids, type=type_, permission_type='DEFINED')
                data.extend(transform.to_sharing_access(r))

                # TODO: get inherited permissions across entire userbase
                # r = ts.metadata.permissions(guids, type=type_, permission_type='EFFECTIVE')

        with console.status(f'[bold green]writing sharing access to {export.name}..[/]'):
            export.dump('ts_sharing_access', data=data)
