from typing import Union, List, Dict, Any
import pathlib
import json
import csv

import typer

from cs_tools.helpers.cli_ux import console
from cs_tools.const import (
    FMT_TSLOAD_DATETIME, FMT_TSLOAD_DATE, FMT_TSLOAD_TIME, FMT_TSLOAD_TRUE_FALSE
)
from cs_tools.util.datetime import to_datetime
from cs_tools.schema.user import PrivilegeEnum
from cs_tools.api import ThoughtSpot


REQUIRED_PRIVILEGES = set([
    PrivilegeEnum.can_administer_thoughtspot,
    PrivilegeEnum.can_manage_data
])


def run_tql_script(
    api: ThoughtSpot,
    *,
    fp: pathlib.Path,
    verbose: bool=False
) -> None:
    """
    Run multiple commands within TQL on a remote server.

    This command is akin to using the shell command cat with TQL.

        cat create-schema.sql | tql

    For further information on TQL, please refer to:
      https://docs.thoughtspot.com/latest/reference/sql-cli-commands.html
      https://docs.thoughtspot.com/latest/reference/tql-service-api-ref.html
    """
    if not set(api.logged_in_user.privileges).intersection(REQUIRED_PRIVILEGES):
        console.print(
            '[red]You do not have the correct privileges to access the remote TQL '
            'service!\n\nYou require at least the "Can Manage Data" privilege.'
            '\n\nPlease consult with your ThoughtSpot Administrator.[/]'
        )
        raise typer.Exit()

    # TODO handle errors found in tql?
    # TODO handle forigveable errors [CREATE TABLE when it exists]
    with fp.open() as f:
        commands = f.read()

    data = {
        'context': {
            'schema': 'falcon_default_schema',
            'server_schema_version': -1
        },
        'script_type': 1,
        'script': commands
    }

    r = api.ts_dataservice.script(data)

    for line in r.iter_lines():
        data = json.loads(line)

        if 'message' in data['result']:
            m = api.ts_dataservice._parse_api_messages(data['result']['message'])

            if verbose:
                console.print(m)

        if 'table' in data['result']:
            m = api.ts_dataservice._parse_tql_query(data['result']['table'])

            if verbose:
                console.print(m)


def run_tql_command(
    api: ThoughtSpot,
    *,
    command: str,
    schema: str='falcon_default_schema',
    verbose: bool=True
) -> None:
    """
    Run a single TQL command on a remote server.

    This command is akin to using the shell command echo with TQL.

        echo SELECT * FROM db.schema.table | tql

    For further information on TQL, please refer to:
      https://docs.thoughtspot.com/latest/reference/sql-cli-commands.html
      https://docs.thoughtspot.com/latest/reference/tql-service-api-ref.html
    """
    if not set(api.logged_in_user.privileges).intersection(REQUIRED_PRIVILEGES):
        console.print(
            '[red]You do not have the correct privileges to access the remote TQL '
            'service!\n\nYou require at least the "Can Manage Data" privilege.'
            '\n\nPlease consult with your ThoughtSpot Administrator.[/]'
        )
        raise typer.Exit()

    # TODO handle errors found in tql?
    # TODO handle forigveable errors [CREATE TABLE when it exists]
    data = {
        'context': {
            'schema': schema,
            'server_schema_version': -1
        },
        'query': {
            'statement': command
        }
    }

    r = api.ts_dataservice.query(data)

    for line in r.iter_lines():
        data = json.loads(line)

        if 'message' in data['result']:
            m = api.ts_dataservice._parse_api_messages(data['result']['message'])

            if verbose:
                console.print(m)

        if 'table' in data['result']:
            m = api.ts_dataservice._parse_tql_query(data['result']['table'])

            if verbose:
                console.print(m)


def tsload(
    api: ThoughtSpot,
    *,
    fp: pathlib.Path,
    target_database: str,
    target_table: str,
    target_schema: str='falcon_default_schema',
    field_separator: str='|',
    empty_target: bool=True,
    verbose: bool=False
) -> Union[str, None]:
    """
    Load a file via tsload on a remote server.

    Defaults to tsload command of:

        tsload --source_file <fp>
               --target_database <target_database>
               --target_schema 'falcon_default_schema'
               --target_table <target_table>
               --field_seprator |
               --boolean_representation true_false
               --null_value ''
               --time_format %H:%M:%S
               --date_format %Y%m%d
               --date_time_format %Y-%m-%d %H:%M:%S
               --has_header_row
               --empty_target

    For further information on tsload, please refer to:
      https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
      https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
      https://docs.thoughtspot.com/latest/reference/data-importer-ref.html
    """
    if not set(api.logged_in_user.privileges).intersection(REQUIRED_PRIVILEGES):
        console.print(
            '[red]You do not have the correct privileges to access the remote tsload '
            'service!\n\nYou require at least the "Can Manage Data" privilege.'
            '\n\nPlease consult with your ThoughtSpot Administrator.[/]'
        )
        raise typer.Exit()

    flags = {
        'target': {
            'database': target_database,
            'schema': target_schema,
            'table': target_table
        },
        'format': {
            'field_separator': field_separator,
            'has_header_row': True,
            'null_value': '',
            'date_time': {
                'date_time_format': FMT_TSLOAD_DATETIME,
                'date_format': FMT_TSLOAD_DATE,
                'time_format': FMT_TSLOAD_TIME
            },
            'boolean': {
                'true_format': FMT_TSLOAD_TRUE_FALSE.split('_')[0],
                'false_format': FMT_TSLOAD_TRUE_FALSE.split('_')[1]
            }
        },
        'load_options': {
            'empty_target': empty_target
        }
    }

    try:
        r = api.ts_dataservice.load_init(flags)
    except Exception as e:
        console.print(
            f'[red]something went wrong trying to access tsload service: {e}[/]'
            f'\nIf you haven\'t enabled tsload service yet, please find the link below '
            f'further information:'
            f'\nhttps://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html'
            f'\n\nHeres the tsload command for the file you tried to load:'
            f'\ntsload --source_file {fp} --target_database {target_database} '
            f'--target_schema {target_schema} --target_table {target_table} '
            f'--field_seprator "{field_separator}" --boolean_representation True_False '
            f'--null_value "" --time_format {FMT_TSLOAD_TIME} --date_format {FMT_TSLOAD_DATE} '
            f'--date_time_format {FMT_TSLOAD_DATETIME} '
            f'--has_header_row '
            + ('--empty_target' if empty_target else '--noempty_target')
        )
        return

    cycle_id = r.json()['cycle_id']

    with fp.open('rb') as file:
        r = api.ts_dataservice.load_start(cycle_id, fd=file)

    if verbose:
        console.print(r.text)

    r = api.ts_dataservice.load_commit(cycle_id)

    if verbose:
        console.print(r.text)

    r = api.ts_dataservice.load_status(cycle_id)
    data = r.json()

    if verbose:
        console.print(
            f'Cycle ID: {data["cycle_id"]}'
            f'\nStarted at {to_datetime(int(data["start_time"]), unit="us")}'
            f'\nStage: {data["internal_stage"]}'
            f'\nRows to write: {data["rows_written"]}'
            f'\nMax ignored rows: {data["ignored_row_count"]}'
        )

    return data['cycle_id']


def to_csv(
    data: List[Dict[str, Any]],
    fp: pathlib.Path,
    *,
    mode: str='w',
    header: bool=True,
    sep: str='|'
):
    """
    Write data to CSV.

    Data must be in record format.. [{column -> value}, ..., {column -> value}]
    """
    with fp.open(mode=mode, encoding='utf-8', newline='') as c:
        writer = csv.DictWriter(c, data[0].keys(), delimiter=sep)

        if header:
            writer.writeheader()

        writer.writerows(data)


# BILL DO U WANT ? :)
#
# def to_excel():
#     """
#     """
#     pass
