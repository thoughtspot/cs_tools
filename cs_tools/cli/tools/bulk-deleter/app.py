from typing import Dict
import logging
import pathlib
import shutil
import enum
import csv

from typer import Argument as A_, Option as O_  # noqa
from openpyxl import load_workbook
import typer

from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT
from cs_tools.cli.ux import CSToolsGroup, CSToolsCommand, console
from cs_tools.cli.tools.common import setup_thoughtspot
from cs_tools.util import chunks


log = logging.getLogger(__name__)
HERE = pathlib.Path(__file__).parent


class ReversibleSystemType(str, enum.Enum):
    """
    Reversible mapping of system to friendly names.
    """
    PINBOARD_ANSWER_BOOK = 'pinboard'
    pinboard = 'PINBOARD_ANSWER_BOOK'
    QUESTION_ANSWER_BOOK = 'saved answer'
    saved_answer = 'QUESTION_ANSWER_BOOK'

    @classmethod
    def to_friendly(cls, value) -> str:
        value = value.strip()

        if '_' not in value:
            return value

        return getattr(cls, value).value

    @classmethod
    def to_system(cls, value) -> str:
        value = value.strip()

        if '_' in value:
            return value

        return getattr(cls, value.replace(' ', '_')).value


def _from_csv(fp: pathlib.Path) -> Dict[str, str]:
    """
    Read data from a CSV.
    """
    with fp.open() as f:
        reader = csv.DictReader(f)
        data = [row for row in reader]

    return data


def _from_excel(fp: pathlib.Path) -> Dict[str, str]:
    """
    Read data from an Excel file.

    This will read data only from the first tab of the workbook.
    """
    wb = load_workbook(filename=fp.as_posix())
    rows = wb.active.rows
    headers = [c.value for c in next(rows)]
    return [dict(zip(headers, [column.value for column in row])) for row in rows]


app = typer.Typer(
    help="""
    Bulk delete metadata objects from your ThoughtSpot platform.

    [b][yellow]USE AT YOUR OWN RISK![/b] This tool uses private API calls which
    could change on any version update and break the tool.[/]
    """,
    cls=CSToolsGroup,
    options_metavar='[--version, --help]',
)


@app.command(cls=CSToolsCommand)
def generate_file(
    export: pathlib.Path = O_(
        ...,
        help='filepath to save generated file to',
        metavar='FILE.csv',
        dir_okay=False,
        resolve_path=True,
        prompt=True
    ),
    # maintained for backwards compatability
    backwards_compat: pathlib.Path = O_(None, '--save_path', help='backwards-compat if specified, directory to save data to', hidden=True)
):
    """
    Generates example file in Excel or CSV format.
    """
    if export.suffix == '.xlsx':
        shutil.copy(HERE / 'static' / 'template.xlsx', export)
    elif export.suffix == '.csv':
        shutil.copy(HERE / 'static' / 'template.csv', export)
    else:
        log.error('appropriate file not supplied, must be either Excel or CSV')
        console.print(f'[red]must provide an Excel (.xlsx) or CSV (.csv) file, got {export}[/]')
        return


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def single(
    ctx: typer.Context,
    type: ReversibleSystemType = O_(..., help='type of the metadata to delete'),
    guid: str = O_(..., help='guid to delete')
):
    """
    Removes a specific object from ThoughtSpot.
    """
    ts = ctx.obj.thoughtspot
    type = ReversibleSystemType.to_system(type.value)

    console.print(f'deleting object .. {type} ... {guid} ... ')

    # NOTE: /metadata/delete WILL NOT error if content does not exist, or if the
    # wrong type & guid are passed. This is a ThoughtSpot API limitation.
    r = ts.api._metadata.delete(type=type, id=[guid])
    log.debug(f'{r} - {r.content}')


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def from_file(
    ctx: typer.Context,
    file: pathlib.Path = A_(
        ...,
        help='path to a file with columns "type" and "guid"',
        metavar='FILE.csv',
        dir_okay=False,
        resolve_path=True
    ),
    batchsize: int = O_(1, help='maximum amount of objects to delete simultaneously')
):
    """
    Remove many objects from ThoughtSpot.

    Accepts an Excel (.xlsx) file or CSV (.csv) file.

    \b
    CSV/XLSX file format should look like..

    \b
        +----------------+-------+
        | type           | guid  |
        +----------------+-------+
        | saved answer   | guid1 |
        | pinboard       | guid2 |
        | ...            | ...   |
        | saved answer   | guid3 |
        +----------------+-------+
    """
    ts = ctx.obj.thoughtspot

    if file.suffix == '.xlsx':
        data = _from_excel(file)
    elif file.suffix == '.csv':
        data = _from_csv(file)
    else:
        log.error('appropriate file type not supplied, must be either Excel or CSV')
        console.print(f'[red]must provide an Excel (.xlsx) or CSV (.csv) file, got {file}[/]')
        return

    #
    # Delete Pinboards
    #
    guids = [_['guid'] for _ in data if ReversibleSystemType.to_friendly(_['type']) == 'pinboard']

    if guids:
        console.print(f'deleting {len(guids)} pinboards')

    for chunk in chunks(guids, n=batchsize):
        if batchsize > 1:
            console.print(f'    deleting {len(chunk)} pinboards')
            log.debug(f'    guids: {chunk}')

        r = ts.api._metadata.delete(type='PINBOARD_ANSWER_BOOK', id=list(chunk))
        log.debug(f'{r} - {r.content}')

    #
    # Delete Answers
    #
    guids = [_['guid'] for _ in data if ReversibleSystemType.to_friendly(_['type']) == 'saved answer']

    if guids:
        console.print(f'deleting {len(guids)} answers')

    for chunk in chunks(guids, n=batchsize):
        if batchsize > 1:
            console.print(f'    deleting {len(chunk)} answers')
            log.debug(f'    guids: {chunk}')

        r = ts.api._metadata.delete(type='QUESTION_ANSWER_BOOK', id=list(chunk))
        log.debug(f'{r} - {r.content}')
