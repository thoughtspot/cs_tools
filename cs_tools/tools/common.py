from collections.abc import Callable
from typing import Union, List, Dict, Any
import logging
import pathlib
import json
import csv

import typer

from cs_tools.helpers.cli_ux import console
from cs_tools.errors import TSLoadServiceUnreachable
from cs_tools.const import (
    FMT_TSLOAD_DATETIME, FMT_TSLOAD_DATE, FMT_TSLOAD_TIME, FMT_TSLOAD_TRUE_FALSE
)
from cs_tools.util.datetime import to_datetime
from cs_tools.thoughtspot import ThoughtSpot
from cs_tools._enums import Privilege


log = logging.getLogger(__name__)
REQUIRED_PRIVILEGES = set([
    Privilege.can_administer_thoughtspot,
    Privilege.can_manage_data
])


class TableAlreadyExists(Exception):
    """
    """


def run_tql_script(
    ts: ThoughtSpot,
    *,
    fp: pathlib.Path,
    verbose: bool=False,
    raise_errors: bool=False
) -> None:
    """
    Run multiple commands within TQL on a remote server.

    This command is akin to using the shell command cat with TQL.

        cat create-schema.sql | tql

    For further information on TQL, please refer to:
      https://docs.thoughtspot.com/latest/reference/sql-cli-commands.html
      https://docs.thoughtspot.com/latest/reference/tql-service-api-ref.html
    """
    if not set(ts.me.privileges).intersection(REQUIRED_PRIVILEGES):
        log.error(
            f'[red]User {ts.me.display_name} do not have the correct privileges to '
            f'access the remote tsload service!\n\nYou require at least the "Can '
            f'Manage Data" privilege.\n\nPlease consult with your ThoughtSpot '
            f'Administrator.[/]'
        )
        raise typer.Exit()

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

    r = ts.api.ts_dataservice.script(data)

    for line in r.iter_lines():
        data = json.loads(line)

        if 'message' in data['result']:
            m = ts.api.ts_dataservice._parse_api_messages(data['result']['message'])

            if raise_errors and 'returned error' in m:
                if 'create table' in m.lower():
                    raise TableAlreadyExists()
                else:
                    raise ValueError(m)

        if 'table' in data['result']:
            m = ts.api.ts_dataservice._parse_tql_query(data['result']['table'])
            log.debug(m)


def run_tql_command(
    ts: ThoughtSpot,
    *,
    command: str,
    schema: str='falcon_default_schema',
    raise_errors: bool=False
) -> None:
    """
    Run a single TQL command on a remote server.

    This command is akin to using the shell command echo with TQL.

        echo SELECT * FROM db.schema.table | tql

    For further information on TQL, please refer to:
      https://docs.thoughtspot.com/latest/reference/sql-cli-commands.html
      https://docs.thoughtspot.com/latest/reference/tql-service-api-ref.html
    """
    if not set(ts.me.privileges).intersection(REQUIRED_PRIVILEGES):
        log.error(
            f'[red]User {ts.me.display_name} do not have the correct privileges to '
            f'access the remote tsload service!\n\nYou require at least the "Can '
            f'Manage Data" privilege.\n\nPlease consult with your ThoughtSpot '
            f'Administrator.[/]'
        )
        raise typer.Exit()

    data = {
        'context': {
            'schema': schema,
            'server_schema_version': -1
        },
        'query': {
            'statement': command
        }
    }

    r = ts.api.ts_dataservice.query(data)

    for line in r.iter_lines():
        data = json.loads(line)

        if 'message' in data['result']:
            m = ts.api.ts_dataservice._parse_api_messages(data['result']['message'])

            if raise_errors and 'returned error' in m:
                raise ValueError(m)

        if 'table' in data['result']:
            m = ts.api.ts_dataservice._parse_tql_query(data['result']['table'])
            log.debug(m)


def tsload(
    ts: ThoughtSpot,
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
               --field_separator '|'
               --boolean_representation True_False
               --null_value ''
               --date_time_format '%Y-%m-%d %H:%M:%S'
               --has_header_row
               --empty_target

    For further information on tsload, please refer to:
      https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
      https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
      https://docs.thoughtspot.com/latest/reference/data-importer-ref.html
    """
    if not set(ts.me.privileges).intersection(REQUIRED_PRIVILEGES):
        log.error(
            f'[red]User {ts.me.display_name} do not have the correct privileges to '
            f'access the remote tsload service!\n\nYou require at least the "Can '
            f'Manage Data" privilege.\n\nPlease consult with your ThoughtSpot '
            f'Administrator.[/]'
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
        r = ts.api.ts_dataservice.load_init(flags)
    except Exception as e:
        raise TSLoadServiceUnreachable(
            f'[red]something went wrong trying to access tsload service: {e}[/]'
            f'\n\nIf you haven\'t enabled tsload service yet, please find the link '
            f'below further information:'
            f'\nhttps://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html'
            f'\n\nHeres the tsload command for the file you tried to load:'
            f'\n\ntsload --source_file {fp} --target_database {target_database} '
            f'--target_schema {target_schema} --target_table {target_table} '
            f'--field_separator "{field_separator}" --boolean_representation True_False '
            f'--null_value "" --time_format "{FMT_TSLOAD_TIME}" '
            f'--date_format "{FMT_TSLOAD_DATE}"'
            f'--date_time_format "{FMT_TSLOAD_DATETIME}" --has_header_row '
            + ('--empty_target' if empty_target else '--noempty_target'),
            http_error=e
        )

    cycle_id = r.json()['cycle_id']

    with fp.open('rb') as file:
        r = ts.api.ts_dataservice.load_start(cycle_id, fd=file)

        if verbose:
            console.print(r.text)

        r = ts.api.ts_dataservice.load_commit(cycle_id)

        if verbose:
            console.print(r.text)

    r = ts.api.ts_dataservice.load_status(cycle_id)
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
    sep: str='|'
):
    """
    Write data to CSV.

    Data must be in record format.. [{column -> value}, ..., {column -> value}]
    """
    header = not fp.exists()

    with fp.open(mode=mode, encoding='utf-8', newline='') as c:
        writer = csv.DictWriter(c, data[0].keys(), delimiter=sep)

        if header:
            writer.writeheader()

        writer.writerows(data)


def check_exists(path: pathlib.Path, *, raise_error: bool=True) -> bool:
    """
    Determine if filepath exists on disk.

    This may optionally raise an error.

    Parameters
    ----------
    path : pathlib.Path
      file path to test

    raise_error : bool = True
      whether or not to raise an error
    """
    if path is None or (path.exists() and not path.is_file()):
        return True

    if raise_error:
        log.error(f'path does not exist: {path}')
        raise typer.Exit()

    return False


def batched(
    api_call: Callable,
    *args,
    batchsize: int=-1,
    offset: Union[int, str]='auto',
    transformer: Callable=None,
    **kwargs
) -> List[Any]:
    """
    Enforce batching on an api call.

    Many API calls take a batchsize parameter. In especially large clusters, it
    can be detrimental to the main node's memory pool to gather all the data at
    once.

    Parameters
    ----------
    api_call : Callable
      bound-method to call on the api

    batchsize : int = -1
      amount of data to load in each successive call to the api, default is everything

    offset : int = -1
      batch offset to fetch page of headers; default is first page

      if this value is 'auto', offset will be determined by the number of
      objects seen so far

    transformer : Callable
      post-processor of the api call, usually used to extract data

    *args, **kwargs
      passed through to the api_call
    """
    responses = []

    if offset == 'auto':
        auto_offset = True
        offset = 0
    else:
        auto_offset = False

    while True:
        r = api_call(*args, batchsize=batchsize, offset=offset, **kwargs)

        if transformer is not None:
            r = transformer(r)

        responses.extend(r)

        # We'll only get a single response
        if batchsize == -1:
            break

        # We only care about a single response
        if not auto_offset:
            break

        offset += len(r)

        # If the response volume is less than the batchsize,
        # we ran out of records to fetch
        if len(r) < batchsize:
            break

    return responses
