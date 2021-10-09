import pathlib

from typer import Argument as A_, Option as O_
import typer

from cs_tools.helpers.cli_ux import console, frontend, RichGroup, RichCommand
from cs_tools.tools.common import tsload
from cs_tools.settings import TSConfig
from cs_tools.thoughtspot import ThoughtSpot


app = typer.Typer(
    help="""
    Enable loading files to ThoughtSpot from a remote machine.

    \b
    For further information on tsload, please refer to:
      https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
      https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
      https://docs.thoughtspot.com/latest/reference/data-importer-ref.html
    """,
    cls=RichGroup
)


@app.command(cls=RichCommand)
@frontend
def status(
    id: str=A_(..., help='data load cycle id'),
    **frontend_kw
):
    """
    Get the status of a data load.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    with ThoughtSpot(cfg) as api:
        r = api.ts_dataservice.load_status(id)
        data = r.json()

    console.print(
        f'Cycle ID: {data["cycle_id"]} ({data["status"]["code"]})'
        f'\nStage: {data["internal_stage"]}'
        f'\nRows written: {data["rows_written"]}'
        f'\nIgnored rows: {data["ignored_row_count"]}'
    )

    # TODO fix this to be prettier...
    if 'parsing_errors' in data:
        errors = '--------'.join(data['parsing_errors'])
        console.print(f'\nErrors in dataload:\n{errors}')


@app.command(cls=RichCommand)
@frontend
def file(
    file: pathlib.Path=A_(..., help='path to file to execute, default to stdin'),
    db: str=O_(..., '--target_database', help='specifies the target database into which tsload should load the data'),
    schema: str=O_('falcon_default_schema', '--target_schema', help='specifies the target schema'),
    table: str=O_(..., '--target_table', help='specifies the target database'),
    empty_target: bool=O_(False, '--empty_target/--noempty_target', show_default='--noempty_target', help='data in the target table is to be removed before the new data is loaded'),
    sep: str=O_('|', '--field_separator', help='field delimiter used in the input file'),
    **frontend_kw
):
    """
    Load a file using the remote tsload service.
    """
    cfg = TSConfig.from_cli_args(**frontend_kw, interactive=True)

    # TODO: this loads files in a single chunk over to the server, there is no
    #       parallelization. We can optimize this in the future if it's desired
    #       and flag for parallel loads or not.
    #
    # DEV NOTE:
    # Data loads can be called for multiple chunks of data for the same cycle ID. All of
    # this data is uploaded to the ThoughtSpot cluster unless a commit load is issued.

    with ThoughtSpot(cfg) as api:
        tsload(
            api, fp=file, target_database=db, target_schema=schema, target_table=table,
            field_separator=sep, empty_target=empty_target
        )
