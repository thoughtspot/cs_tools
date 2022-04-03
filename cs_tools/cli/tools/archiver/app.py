from typing import Any, Dict, List, Tuple
import datetime as dt
import logging
import pathlib

from typer import Argument as A_, Option as O_  # noqa
import click
import typer

from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT
from cs_tools.cli.tools import common
from cs_tools.cli.util import base64_to_file
from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand
from cs_tools.errors import ContentDoesNotExist

from .enums import ContentType, UserActions
from .util import DataTable, to_datetime


log = logging.getLogger(__name__)


def _get_content(ts, *, tags) -> Tuple[List[Dict[str, Any]]]:
    try:
        answers = [{'content_type': 'answer', **_} for _ in ts.answer.all(tags=tags)]
    except ContentDoesNotExist:
        answers = []

    try:
        pinboards = [{'content_type': 'pinboard', **_} for _ in ts.pinboard.all(tags=tags)]
    except ContentDoesNotExist:
        pinboards = []

    return answers, pinboards


app = typer.Typer(
    help="""
    Manage stale answers and pinboards within your platform.

    As your platform grows, users will create and use answers and pinboards.
    Sometimes, users will create content for temporary exploratory purpopses
    and then abandon it for newer pursuits. Archiver enables you to identify,
    tag, export, and remove that potentially abandoned content.
    """,
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=common.setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def identify(
    ctx: click.Context,
    tag: str=O_('TO BE ARCHIVED', help='tag name to use for labeling objects to archive'),
    content: ContentType=O_('all', help='type of content to archive'),
    usage_months: int=O_(
        999,
        show_default=False,
        help='months to consider for user activity (default: all user history)'
    ),
    ignore_recent: int=O_(
        30,
        help='window of days to ignore for newly created or modified content'
    ),
    # TODO?
    #
    # ignore_tags: List[str]=O_(
    #     None,
    #     callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
    #     help='content with these tags will be ignored',
    # ),
    dry_run: bool=O_(
        False,
        '--dry-run',
        show_default=False,
        help='test selection criteria, do not apply tags and instead output '
             'information to console on content to be archived'
    ),
    no_prompt: bool=O_(
        False,
        '--no-prompt',
        show_default=False,
        help='disable the confirmation prompt'
    ),
    report: pathlib.Path=O_(
        None,
        help='generates a list of content to be archived',
        metavar='FILE.csv',
        dir_okay=False,
        resolve_path=True
    )
):
    """
    Identify objects which objects can be archived.

    [yellow]Identification criteria will skip content owned by "System User" (system)
    and "Administrator" (tsamin)[/]

    ThoughtSpot stores usage activity (by default, 6 months of interactions) by user in
    the platform. If a user views, edits, or creates an Answer or Pinboard, ThoughtSpot
    knows about it. This can be used as a proxy to understanding what content is
    actively being used.
    """
    ts = ctx.obj.thoughtspot
    actions = UserActions.strigified(sep="', '", context=content)

    recently = dt.datetime.now(tz=ts.platform.tz) - dt.timedelta(days=ignore_recent)

    with console.status('[bold green]retrieving objects usage..[/]'):
        data = ts.search(
            f"[user action] = '{actions}' "
            f"[timestamp].'last {usage_months} months' "
            r"[timestamp].'this month' "
            r"[answer book guid]",
            worksheet='TS: BI Server'
        )

    # Currently used GUIDs (within the past {months} months ...)
    usage = set(_['Answer Book GUID'] for _ in data)

    # Repository of all available GUIDs
    data = []

    if content.value in ('all', 'answer'):
        with console.status('[bold green]retrieving existing answers..[/]'):
            try:
                data.extend({**a, 'content_type': 'answer'} for a in ts.answer.all())
            except ContentDoesNotExist:
                pass

    if content.value in ('all', 'pinboard'):
        with console.status('[bold green]retrieving existing pinboards..[/]'):
            try:
                data.extend({**p, 'content_type': 'pinboard'} for p in ts.pinboard.all())
            except ContentDoesNotExist:
                pass

    archive = set(_['id'] for _ in data) - usage

    to_archive = [
        {
            'content_type': _['content_type'],
            'guid': _['id'],
            'name': _['name'],
            'created_at': to_datetime(_['created'], tz=ts.platform.timezone, friendly=True),
            'last_modified': to_datetime(_['modified'], tz=ts.platform.timezone, friendly=True),
            'by': _['authorName']
        }
        for _ in data
        # ignore recent content
        if to_datetime(_['created'], tz=ts.platform.timezone) <= recently
        if to_datetime(_['modified'], tz=ts.platform.timezone) <= recently
        # only include content found in the metadata snapshot
        if _['id'] in archive
    ]

    if not to_archive:
        console.log('no stale content found')
        raise typer.Exit()

    table = DataTable(
                to_archive,
                title=f"[green]Archive Results[/]: Tagging content with [cyan]'{tag}'[/]",
                caption=f'Total of {len(to_archive)} items tagged.. ({len(data)} in platform)'
            )

    console.log('\n', table)

    if report is not None:
        common.to_csv(to_archive, fp=report, header=True)

    if dry_run:
        raise typer.Exit(-1)

    tag = ts.tag.get(tag, create_if_not_exists=True)

    answers = [_['guid'] for _ in to_archive if _['content_type'] == 'answer']
    pinboards = [_['guid'] for _ in to_archive if _['content_type'] == 'pinboard']

    # PROMPT FOR INPUT
    if not no_prompt:
        typer.confirm(
            f'\nWould you like to continue with tagging {len(to_archive)} objects?',
            abort=True
        )

    if answers:
        ts.api._metadata.assigntag(
            id=answers,
            type=['QUESTION_ANSWER_BOOK' for _ in answers],
            tagid=[tag['id'] for _ in answers]
        )

    if pinboards:
        ts.api._metadata.assigntag(
            id=pinboards,
            type=['PINBOARD_ANSWER_BOOK' for _ in pinboards],
            tagid=[tag['id'] for _ in pinboards]
        )


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=common.setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def revert(
    ctx: typer.Context,
    tag: str=O_('TO BE ARCHIVED', help='tag name to remove on labeled objects'),
    delete_tag: bool=O_(
        False,
        '--delete-tag',
        show_default=False,
        help='remove the tag itself, after untagging identified objects'
    ),
    dry_run: bool=O_(
        False,
        '--dry-run',
        show_default=False,
        help='test selection criteria, do not remove tags and instead output '
             'information on content to be unarchived'
    ),
    no_prompt: bool=O_(
        False,
        '--no-prompt',
        show_default=False,
        help='disable the confirmation prompt'
    ),
    report: pathlib.Path=O_(
        None,
        help='generates a list of content to be untagged',
        metavar='FILE.csv',
        dir_okay=False,
        resolve_path=True
    )
):
    """
    Remove objects from the temporary archive.
    """
    ts = ctx.obj.thoughtspot

    to_unarchive = []
    answers, pinboards = _get_content(ts, tags=tag)

    to_unarchive.extend(
        {
            'content_type': _['content_type'],
            'guid': _['id'],
            'name': _['name'],
            'created_at': to_datetime(_['created'], tz=ts.platform.timezone, friendly=True),
            'last_modified': to_datetime(_['modified'], tz=ts.platform.timezone, friendly=True),
            'by': _['authorName']
        }
        for _ in (*answers, *pinboards)
    )

    if not to_unarchive:
        console.log(f"no content found with the tag '{tag}'")
        raise typer.Exit()

    table = DataTable(
                to_unarchive,
                title=f"[green]Unarchive Results[/]: Untagging content with [cyan]'{tag}'[/]",
                caption=f'Total of {len(to_unarchive)} items tagged..'
            )

    console.log('\n', table)

    if report is not None:
        common.to_csv(to_unarchive, fp=report, header=True)

    if dry_run:
        raise typer.Exit()

    tag = ts.tag.get(tag)

    answers = [content['guid'] for content in to_unarchive if content['content_type'] == 'answer']
    pinboards = [content['guid'] for content in to_unarchive if content['content_type'] == 'pinboard']

    # PROMPT FOR INPUT
    if not no_prompt:
        typer.confirm(
            f'\nWould you like to continue with untagging {len([*answers, *pinboards])} objects?',
            abort=True
        )

    if answers:
        ts.api._metadata.unassigntag(
            id=answers,
            type=['QUESTION_ANSWER_BOOK' for _ in answers],
            tagid=[tag['id'] for _ in answers]
        )

    if pinboards:
        ts.api._metadata.unassigntag(
            id=pinboards,
            type=['QUESTION_ANSWER_BOOK' for _ in pinboards],
            tagid=[tag['id'] for _ in pinboards]
        )

    if delete_tag:
        ts.tag.delete(tag['name'])


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=common.setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def remove(
    ctx: typer.Context,
    tag: str=O_('TO BE ARCHIVED', help='tag name to remove on labeled objects'),
    export_tml: pathlib.Path=O_(
        None,
        help='if set, path to export tagged objects as a zipfile',
        metavar='FILE.zip',
        dir_okay=False,
        resolve_path=True
    ),
    delete_tag: bool=O_(
        False,
        '--delete-tag',
        show_default=False,
        help='remove the tag after deleting identified objects'
    ),
    export_only: bool=O_(
        False,
        '--export-only',
        show_default=False,
        help='export all tagged content, but do not remove it from that platform'
    ),
    dry_run: bool=O_(
        False,
        '--dry-run',
        show_default=False,
        help=(
            'test selection criteria, does not export/delete content and instead '
            'output information to console on content to be unarchived'
        )
    ),
    no_prompt: bool=O_(
        False,
        '--no-prompt',
        show_default=False,
        help='disable the confirmation prompt'
    ),
    report: pathlib.Path=O_(
        None,
        help='generates a list of content to be removed',
        metavar='FILE.csv',
        dir_okay=False,
        resolve_path=True
    )
):
    """
    Remove objects from the ThoughtSpot platform.
    """
    ts = ctx.obj.thoughtspot

    if export_tml is not None:
        if not export_tml.as_posix().endswith('zip'):
            console.log(
                f"[b red]TML export path must be a zip file! Got, '{export_tml}'"
            )
            raise typer.Exit(-1)

        if export_tml.exists():
            console.log(f'[b red]Zip file "{export_tml}" already exists!')
            typer.confirm('Would you like to overwrite it?', abort=True)

    to_unarchive = []
    answers, pinboards = _get_content(ts, tags=tag)

    to_unarchive.extend(
        {
            'content_type': _['content_type'],
            'guid': _['id'],
            'name': _['name'],
            'created_at': to_datetime(_['created'], tz=ts.platform.timezone, friendly=True),
            'last_modified': to_datetime(_['modified'], tz=ts.platform.timezone, friendly=True),
            'by': _['authorName']
        }
        for _ in (*answers, *pinboards)
    )

    if not to_unarchive:
        console.log(f"no content found with the tag '{tag}'")
        raise typer.Exit()

    _mod = '' if export_tml is None else ' and exporting '
    table = DataTable(
                to_unarchive,
                title=f"[green]Remove Results[/]: Removing{_mod} content with [cyan]'{tag}'[/]",
                caption=f'Total of {len(to_unarchive)} items tagged..'
            )

    console.log('\n', table)

    if report is not None:
        common.to_csv(to_unarchive, fp=report, header=True)

    if dry_run:
        raise typer.Exit()

    tag = ts.tag.get(tag)
    answers = [_['guid'] for _ in to_unarchive if _['content_type'] == 'answer']
    pinboards = [_['guid'] for _ in to_unarchive if _['content_type'] == 'pinboard']

    # PROMPT FOR INPUT
    if not no_prompt:

        if export_only:
            op = 'exporting'
        elif export_tml:
            op = 'exporting and removing'
        else:
            op = 'removing'

        typer.confirm(
            f'\nWould you like to continue with {op} {len([*answers, *pinboards])} objects?',
            abort=True
        )

    if export_tml is not None:
        r = ts.api._metadata.edoc_export_epack(
                request={
                    'object': [
                        *[{'id': id, 'type': 'QUESTION_ANSWER_BOOK'} for id in answers],
                        *[{'id': id, 'type': 'PINBOARD_ANSWER_BOOK'} for id in pinboards]
                    ],
                    'export_dependencies': False
                }
            )

        if not r.json().get('zip_file'):
            console.log(
                '[b red]attempted to export TML, but the API response failed, '
                'please re-run the command with --verbose flag to capture more log '
                'details'
            )
            raise typer.Exit(-1)

        base64_to_file(r.json()['zip_file'], filepath=export_tml)

    if export_only:
        raise typer.Exit()

    if answers:
        ts.api._metadata.delete(id=answers, type='QUESTION_ANSWER_BOOK')

    if pinboards:
        ts.api._metadata.delete(id=pinboards, type='PINBOARD_ANSWER_BOOK')

    if delete_tag:
        ts.tag.delete(tag['name'])
