import datetime as dt
import pathlib

from typer import Argument as A_, Option as O_
import typer

from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT
from cs_tools.cli.ux import console, CSToolsGroup, CSToolsCommand, SyncerProtocolType
from cs_tools.const import (
    FMT_TSLOAD_DATETIME, FMT_TSLOAD_DATE, FMT_TSLOAD_TIME, FMT_TSLOAD_TRUE_FALSE
)
from cs_tools.cli.tools import common


app = typer.Typer(
    help="""
    Enable loading files to ThoughtSpot from a remote machine.

    \b
    For further information on tsload, please refer to:
      https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
      https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
      https://docs.thoughtspot.com/latest/reference/data-importer-ref.html
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
def status(
    ctx: typer.Context,
    cycle_id: str=A_(..., help='data load cycle id'),
    bad_records: str = O_(
        None,
        '--bad_records_file',
        help='file to use for storing rows that failed to load',
        metavar='protocol://DEFINITION.toml',
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    )
):
    """
    Get the status of a data load.
    """
    ts = ctx.obj.thoughtspot

    with console.status('[bold green]Waiting for data load to complete..'):
        data = ts.tsload.status(cycle_id, wait_for_complete=True)
        console.print(
            f'\nCycle ID: {data["cycle_id"]} ({data["status"]["code"]})'
            f'\nStage: {data["internal_stage"]}'
            f'\nRows written: {data["rows_written"]}'
            f'\nIgnored rows: {data["ignored_row_count"]}'
        )

    if data['ignored_row_count'] > 0:
        now = dt.datetime.now().strftime('%Y-%m-%dT%H_%M_%S')
        fp = f'BAD_RECORDS_{now}_{cycle_id}'
        console.print(
            f'[red]\n\nBad records found...\n\twriting to {bad_records.directory / fp}'
        )
        data = ts.tsload.bad_records(cycle_id)
        bad_records.dump(fp, data=data)

    if data['status']['code'] == 'LOAD_FAILED':
        console.print(f'\nFailure reason:\n  [red]{data["status"]["message"]}[/]')


@app.command(cls=CSToolsCommand)
@depends(
    thoughtspot=common.setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    enter_exit=True
)
def file(
    ctx: typer.Context,
    file: pathlib.Path = A_(..., help='path to file to execute', metavar='FILE.csv', dir_okay=False, resolve_path=True),
    target_database: str = O_(..., '--target_database', help='specifies the target database into which tsload should load the data'),
    target_table: str = O_(..., '--target_table', help='specifies the target database'),
    target_schema: str = O_('falcon_default_schema', '--target_schema', help='specifies the target schema'),
    empty_target: bool = O_(False, '--empty_target/--noempty_target', show_default=False, help='data in the target table is to be removed before the new data is loaded (default: --noempty_target)'),
    max_ignored_rows: int = O_(0, '--max_ignored_rows', help='maximum number of rows that can be ignored for successful load. If number of ignored rows exceeds this limit, the load is aborted'),
    date_format: str = O_(FMT_TSLOAD_DATE, '--date_format', help='format string for date values, accepts format spec by the strptime datetime library'),
    date_time_format: str = O_(FMT_TSLOAD_DATETIME, '--date_time_format', help='format string for datetime values, accepts format spec by the strptime datetime library'),
    time_format: str = O_(FMT_TSLOAD_TIME, '--time_format', help='format string for time values, accepts format spec by the strptime datetime library'),
    skip_second_fraction: bool = O_(False, '--skip_second_fraction', show_default=False, help='when true, skip fractional part of seconds: milliseconds, microseconds, or nanoseconds from either datetime or time values if that level of granularity is present in the source data'),
    field_separator: str = O_('|', '--field_separator', help='field delimiter used in the input file'),
    null_value: str = O_('', '--null_value', help='escape character in source data'),
    boolean_representation: str = O_(FMT_TSLOAD_TRUE_FALSE, '--boolean_representation', help='format in which boolean values are represented'),
    has_header_row: bool = O_(False, '--has_header_row', show_default=False, help='indicates that the input file contains a header row'),
    escape_character: str = O_('"', '--escape_character', help='specifies the escape character used in the input file'),
    enclosing_character: str = O_('"', '--enclosing_character', help='enclosing character in csv source format'),
    bad_records: str = O_(
        None,
        '--bad_records_file',
        help='file to use for storing rows that failed to load',
        metavar='protocol://DEFINITION.toml',
        callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    ),
    flexible: bool = O_(False, '--flexible', show_default=False, help='whether input data file exactly matches target schema', hidden=True)
):
    """
    Load a file using the remote tsload service.
    """
    ts = ctx.obj.thoughtspot

    # TODO: this loads files in a single chunk over to the server, there is no
    #       parallelization. We can optimize this in the future if it's desired
    #       and flag for parallel loads or not.
    #
    # DEV NOTE:
    # Data loads can be called for multiple chunks of data for the same cycle ID. All of
    # this data is uploaded to the ThoughtSpot cluster unless a commit load is issued.
    #

    opts = {
        'target_database': target_database,
        'target_table': target_table,
        'target_schema': target_schema,
        'empty_target': empty_target,
        'max_ignored_rows': max_ignored_rows,
        'date_format': date_format,
        'date_time_format': date_time_format,
        'time_format': time_format,
        'skip_second_fraction': skip_second_fraction,
        'field_separator': field_separator,
        'null_value': null_value,
        'boolean_representation': boolean_representation,
        'has_header_row': has_header_row,
        'flexible': flexible,
        'escape_character': escape_character,
        'enclosing_character': enclosing_character
    }

    with console.status(f'[bold green]Loading {file} to ThoughtSpot..'):
        cycle_id = ts.tsload.upload(ts, fp=file, **opts, verbose=True)

    if bad_records is None:
        return

    with console.status('[bold green]Waiting for data load to complete..'):
        data = ts.tsload.status(cycle_id, wait_for_complete=True)

    if data['ignored_row_count'] > 0:
        now = dt.datetime.now().strftime('%Y-%m-%dT%H_%M_%S')
        fp = f'BAD_RECORDS_{now}_{cycle_id}'
        console.print(
            f'[red]\n\nBad records found...\n\twriting to {bad_records.directory / fp}'
        )
        data = ts.tsload.bad_records(cycle_id)
        bad_records.dump(fp, data=data)
