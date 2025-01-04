from __future__ import annotations

import pathlib

import typer

from cs_tools.cli.dependencies import thoughtspot
from cs_tools.cli.ux import CSToolsApp, rich_console

from .const import FMT_TSLOAD_DATE, FMT_TSLOAD_DATETIME, FMT_TSLOAD_TIME, FMT_TSLOAD_TRUE_FALSE

app = CSToolsApp(
    help="""
    Enable loading files to ThoughtSpot from a remote machine.

    \b
    For further information on tsload, please refer to:
      https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
      https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
      https://docs.thoughtspot.com/latest/reference/data-importer-ref.html
    """,
)


@app.command(dependencies=[thoughtspot])
def status(
    ctx: typer.Context,
    cycle_id: str = typer.Argument(..., help="data load cycle id"),
    # bad_records: str = typer.Option(
    #     None,
    #     '--bad_records_file',
    #     help='file to use for storing rows that failed to load',
    #     metavar='protocol://DEFINITION.toml',
    #     callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    # )
):
    """
    Get the status of a data load.
    """
    ts = ctx.obj.thoughtspot

    with rich_console.status("[bold green]Waiting for data load to complete.."):
        data = ts.tsload.status(cycle_id, wait_for_complete=True)
        rich_console.print(
            f"\nCycle ID: {data['cycle_id']} ({data['status']['code']})"
            f"\nStage: {data['internal_stage']}"
            f"\nRows written: {data['rows_written']}"
            f"\nIgnored rows: {data['ignored_row_count']}"
        )

    # if int(data['ignored_row_count']) > 0:
    #     now = dt.datetime.now(tz=dt.timezone.utc).strftime('%Y-%m-%dT%H_%M_%S')
    #     fp = f'BAD_RECORDS_{now}_{cycle_id}'
    #     console.print(
    #         f'[red]\n\nBad records found...\n\twriting to {bad_records.directory / fp}'
    #     )
    #     data = ts.tsload.bad_records(cycle_id)
    #     bad_records.dump(fp, data=data)

    if data["status"]["code"] == "LOAD_FAILED":
        rich_console.print(f"\nFailure reason:\n  [red]{data['status']['message']}[/]")

    if data.get("parsing_errors", False):
        rich_console.print(f"[red]{data['parsing_errors']}")


@app.command(dependencies=[thoughtspot])
def file(
    ctx: typer.Context,
    file: pathlib.Path = typer.Argument(
        ..., help="path to file to execute", metavar="FILE.csv", dir_okay=False, resolve_path=True
    ),
    target_database: str = typer.Option(
        ..., "--target_database", help="specifies the target database into which tsload should load the data"
    ),
    target_table: str = typer.Option(..., "--target_table", help="specifies the target database"),
    target_schema: str = typer.Option("falcon_default_schema", "--target_schema", help="specifies the target schema"),
    empty_target: bool = typer.Option(
        False,
        "--empty_target/--noempty_target",
        show_default=False,
        help="data in the target table is to be removed before the new data is loaded (default: --noempty_target)",
    ),
    max_ignored_rows: int = typer.Option(
        0,
        "--max_ignored_rows",
        help=(
            "maximum number of rows that can be ignored for successful load. If number of ignored rows exceeds this "
            "limit, the load is aborted"
        ),
    ),
    date_format: str = typer.Option(
        FMT_TSLOAD_DATE,
        "--date_format",
        help="format string for date values, accepts format spec by the strptime datetime library",
    ),
    date_time_format: str = typer.Option(
        FMT_TSLOAD_DATETIME,
        "--date_time_format",
        help="format string for datetime values, accepts format spec by the strptime datetime library",
    ),
    time_format: str = typer.Option(
        FMT_TSLOAD_TIME,
        "--time_format",
        help="format string for time values, accepts format spec by the strptime datetime library",
    ),
    skip_second_fraction: bool = typer.Option(
        False,
        "--skip_second_fraction",
        show_default=False,
        help=(
            "when true, skip fractional part of seconds: milliseconds, microseconds, or nanoseconds from either "
            "datetime or time values if that level of granularity is present in the source data"
        ),
    ),
    field_separator: str = typer.Option("|", "--field_separator", help="field delimiter used in the input file"),
    null_value: str = typer.Option("", "--null_value", help="escape character in source data"),
    boolean_representation: str = typer.Option(
        FMT_TSLOAD_TRUE_FALSE, "--boolean_representation", help="format in which boolean values are represented"
    ),
    has_header_row: bool = typer.Option(
        False, "--has_header_row", show_default=False, help="indicates that the input file contains a header row"
    ),
    escape_character: str = typer.Option(
        '"', "--escape_character", help="specifies the escape character used in the input file"
    ),
    enclosing_character: str = typer.Option(
        '"', "--enclosing_character", help="enclosing character in csv source format"
    ),
    # bad_records: str = typer.Option(
    #     None,
    #     '--bad_records_file',
    #     help='file to use for storing rows that failed to load',
    #     metavar='protocol://DEFINITION.toml',
    #     callback=lambda ctx, to: SyncerProtocolType().convert(to, ctx=ctx)
    # ),
    flexible: bool = typer.Option(
        False,
        "--flexible",
        show_default=False,
        help="whether input data file exactly matches target schema",
        hidden=True,
    ),
    http_timeout: int = typer.Option(False, "--timeout", help="network call timeout threshold"),
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
        "database": target_database,
        "table": target_table,
        "schema_": target_schema,
        "empty_target": empty_target,
        "max_ignored_rows": max_ignored_rows,
        "date_format": date_format,
        "date_time_format": date_time_format,
        "time_format": time_format,
        "skip_second_fraction": skip_second_fraction,
        "field_separator": field_separator,
        "null_value": null_value,
        "boolean_representation": boolean_representation,
        "has_header_row": has_header_row,
        "flexible": flexible,
        "escape_character": escape_character,
        "enclosing_character": enclosing_character,
    }

    with rich_console.status(f"[bold green]Loading [yellow]{file}[/] to ThoughtSpot.."):
        with file.open("r", encoding="utf-8", newline="") as fd:
            cycle_id = ts.tsload.upload(fd, **opts, http_timeout=http_timeout)

    rich_console.log(f"Data load cycle_id: [cyan]{cycle_id}")

    # if bad_records is None:
    #     return

    # with console.status('[bold green]Waiting for data load to complete..'):
    #     data = ts.tsload.status(cycle_id, wait_for_complete=True)

    # if data['ignored_row_count'] > 0:
    #     now = dt.datetime.now(tz=dt.timezone.utc).strftime('%Y-%m-%dT%H_%M_%S')
    #     fp = f'BAD_RECORDS_{now}_{cycle_id}'
    #     console.print(
    #         f'[red]\n\nBad records found...\n\twriting to {bad_records.directory / fp}'
    #     )
    #     data = ts.tsload.bad_records(cycle_id)
    #     bad_records.dump(fp, data=data)
