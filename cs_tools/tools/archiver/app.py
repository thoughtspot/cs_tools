import pathlib
import enum

from typer import Argument as A_, Option as O_  # noqa
from rich.table import Table
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.settings import TSConfig
from cs_tools.thoughtspot import ThoughtSpot


class ContentType(enum.Enum):
    answer = 'answer'
    pinboard = 'pinboard'
    all = 'all'


class UserActions(enum.Enum):
    view_answer = 'ANSWER_VIEW'
    view_pinboard = 'PINBOARD_VIEW'
    view_embed_pinboard = 'PINBOARD_TSPUBLIC_RUNTIME_FILTER'
    view_embed_filtered_pinboard_view = 'PINBOARD_TSPUBLIC_NO_RUNTIME_FILTER'

    @classmethod
    def strigified(cls, sep: str=' ', context: str=None) -> str:
        mapper = {
            'answer': ['ANSWER_VIEW'],
            'pinboard': [
                'PINBOARD_VIEW',
                'PINBOARD_TSPUBLIC_RUNTIME_FILTER',
                'PINBOARD_TSPUBLIC_NO_RUNTIME_FILTER'
            ]
        }
        allowed = mapper.get(context, [_.value for _ in cls])
        return sep.join([_.value for _ in cls if _.value in allowed])


app = typer.Typer(
    help="""
    Manage stale answers and pinboards within your platform.

    As your platform grows, users will create and use answers and pinboards.
    Sometimes, users will create content for temporary exploratory purpopses
    and then abandon it for newer pursuits. Archiver enables you to identify,
    tag, export, and remove that potentially abandoned content.
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def fetch(
    tag: str=O_('TO BE ARCHIVED', help='tag name to use for labeling objects to archive'),
    content: ContentType=O_('all', help='type of content to archive'),
    usage_months: int=O_(
        999,
        show_default=False,
        help='months to consider for user activity (default: all user history)'
    ),
    dry_run: bool=O_(
        False,
        '--dry-run',
        show_default=False,
        help='test selection criteria, do not apply tags and instead output information on content to be archived'
    ),
    **frontend_kw
):
    """
    Identify objects which objects can be archived.

    ThoughtSpot stores usage activity (by default, 6 months of interactions) by user in
    the platform. If a user views, edits, or creates an Answer or Pinboard, ThoughtSpot
    knows about it. This can be used as a proxy to understanding what content is
    actively being used.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)
    actions = UserActions.strigified(sep="', '", context=content)

    with ThoughtSpot(cfg) as ts:
        data = ts.search(
            f"[user action] = '{actions}' "
            f"[timestamp].'last {usage_months} months' "
            f"[timestamp].'this month' "
            f"[answer book guid]",
            worksheet='TS: BI Server'
        )

        # Currently used GUIDs (within the past {months} months ...)
        usage = set(_['Answer Book GUID'] for _ in data)

        # Repository of all available GUIDs
        data = []

        if content.value in ('all', 'answer'):
            r = ts.api._metadata.list(type='QUESTION_ANSWER_BOOK', showhidden=False, auto_created=False)
            data.extend(
                {'content_type': 'answer', **_}
                for _ in r.json()['headers']
                if _['authorName'] not in ('tsadmin', 'system')
            )

        if content.value in ('all', 'pinboard'):
            r = ts.api._metadata.list(type='PINBOARD_ANSWER_BOOK', showhidden=False, auto_created=False)
            data.extend(
                {'content_type': 'pinboard', **_}
                for _ in r.json()['headers']
                if _['authorName'] not in ('tsadmin', 'system')
            )

        #
        #
        #

        archive = set(_['id'] for _ in data) - usage

        to_archive = [
            {'content_type': _['content_type'], 'guid': _['id'], 'name': _['name']}
            for _ in data if _['id'] in archive
        ]

        #
        #
        #

        table = Table(
            *to_archive[0].keys(),
            title=f"[green]Archive Results[/]: Tagging content with [cyan]'{tag}'[/]",
            caption=f'Total of {len(to_archive)} items tagged.. ({len(data)} seen)'
        )
        [table.add_row(*r.values()) for r in to_archive[:3]]
        [table.add_row('...', '...', '...')]
        [table.add_row(*r.values()) for r in to_archive[-3:]]
        console.log('\n', table)

        if dry_run:
            raise typer.Exit(-1)

        #
        #
        #

        r = ts.api._metadata.list(type='TAG')
        tag_exists = [_ for _ in r.json()['headers'] if _['name'].casefold() == tag.casefold()]

        if not tag_exists:
            r = ts.api._metadata.create(name=tag, type='TAG')
            tag_guid = r.json()['header']['id']
        else:
            tag_guid = tag_exists[0]['id']

        #
        #
        #

        answers = [content['guid'] for content in to_archive if content['content_type'] == 'answer']
        ts.api._metadata.assigntag(
            id=answers,
            type=['QUESTION_ANSWER_BOOK' for _ in answers],
            tagid=[tag_guid for _ in answers]
        )

        pinboards = [content['guid'] for content in to_archive if content['content_type'] == 'pinboard']
        ts.api._metadata.assigntag(
            id=pinboards,
            type=['PINBOARD_ANSWER_BOOK' for _ in pinboards],
            tagid=[tag_guid for _ in pinboards]
        )


@app.command(cls=RichCommand)
@frontend
def annul(
    tag: str=O_('TO BE ARCHIVED', help='tag name to remove on labeled objects'),
    dry_run: bool=O_(
        False,
        '--dry-run',
        show_default=False,
        help='test selection criteria, do not remove tags and instead output information on content to be unarchived'
    ),
    **frontend_kw
):
    """
    Remove objects from the temporary archive.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as ts:
        to_unarchive = []

        r = ts.api._metadata.list(type='QUESTION_ANSWER_BOOK', tagname=[tag])
        to_unarchive.extend({'content_type': 'answer', **_} for _ in r.json()['headers'])

        r = ts.api._metadata.list(type='PINBOARD_ANSWER_BOOK', tagname=[tag])
        to_unarchive.extend({'content_type': 'pinboard', **_} for _ in r.json()['headers'])

        #
        #
        #

        if not to_unarchive:
            console.log(f'no content found with the tag "{tag}"')
            raise typer.Exit()

        table = Table(
            *to_unarchive[0].keys(),
            title=f"[green]Unarchive Results[/]: Untagging content with [cyan]'{tag}'[/]",
            caption=f'Total of {len(to_unarchive)} items tagged..'
        )
        [table.add_row(*r.values()) for r in to_unarchive[:3]]
        [table.add_row('...', '...', '...')]
        [table.add_row(*r.values()) for r in to_unarchive[-3:]]
        console.log('\n', table)

        if dry_run:
            raise typer.Exit()

        #
        #
        #

        r = ts.api._metadata.list(type='TAG')
        tag_exists = [_ for _ in r.json()['headers'] if _['name'].casefold() == tag.casefold()]

        if not tag_exists:
            r = ts.api._metadata.create(name=tag, type='TAG')
            tag_guid = r.json()['header']['id']
        else:
            tag_guid = tag_exists[0]['id']

        #
        #
        #

        answers = [content['id'] for content in to_unarchive if content['content_type'] == 'answer']
        ts.api._metadata.unassigntag(
            id=answers,
            type=['QUESTION_ANSWER_BOOK' for _ in answers],
            tagid=[tag_guid for _ in answers]
        )

        pinboards = [content['id'] for content in to_unarchive if content['content_type'] == 'pinboard']
        ts.api._metadata.unassigntag(
            id=pinboards,
            type=['QUESTION_ANSWER_BOOK' for _ in pinboards],
            tagid=[tag_guid for _ in pinboards]
        )


@app.command(cls=RichCommand)
@frontend
def delete(
    tag: str=O_('TO BE ARCHIVED', help='tag name to remove on labeled objects'),
    export: pathlib.Path=O_(None, help='directory to export tagged objects, as TML'),
    dry_run: bool=O_(
        False,
        '--dry-run',
        show_default=False,
        help=(
            'test selection criteria, does not export/delete content and instead '
            'output information on content to be unarchived'
        )
    ),
    **frontend_kw
):
    """
    Remove objects from the ThoughtSpot platform.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as ts:
        console.error('This command has yet to be implemented.')
        raise typer.Exit(-1)
