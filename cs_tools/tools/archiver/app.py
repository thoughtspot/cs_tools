import pathlib
import enum

from typer import Argument as A_, Option as O_  # noqa
import click
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
    Archiver.

    Solution should help the customer identify objects which have not
    been visited within a certain timeframe.
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def fetch(
    tag: str=O_('TO BE ARCHIVED', help='tag name to use for labeling objects to archive'),
    content: ContentType=O_('all', help=''),
    months: int=O_(999, show_default=False, help=''),
    dry_run: bool=O_(False, '--dry-run', show_default=False, help=''),
    **frontend_kw
):
    """
    Identify objects which objects can be archived.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)
    actions = UserActions.strigified(sep="', '", context=content)

    with ThoughtSpot(cfg) as ts:
        data = ts.search(
            f"[user action] = '{actions}' [timestamp].'last {months} months' [answer book guid]",
            worksheet='TS: BI Server'
        )

        if dry_run:
            print(data)
            raise typer.Exit(-1)

        ...


@app.command(cls=RichCommand)
@frontend
def annul(
    # tag: str=O_(),
    # dry_run: bool=O_(),
    **frontend_kw
):
    """
    Unarchive objects.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as ts:
        ...


@app.command(cls=RichCommand)
@frontend
def delete(
    # tag: str=O_(),
    # months: int=O_(),
    # export: pathlib.Path=O_(),
    # dry_run: bool=O_(),
    **frontend_kw
):
    """
    Remove objects from the platform.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as ts:
        ...
