from typing import Any, Dict, List, Union
from io import BufferedIOBase, TextIOWrapper
from tempfile import _TemporaryFileWrapper
import datetime as dt
import logging
import json
import time

from pydantic import validate_arguments

from cs_tools.data.enums import Privilege
from cs_tools.errors import InsufficientPrivileges, TSLoadServiceUnreachable
from cs_tools.const import (
    FMT_TSLOAD_DATETIME, FMT_TSLOAD_DATE, FMT_TSLOAD_TIME, FMT_TSLOAD_TRUE_FALSE,
    APP_DIR
)


log = logging.getLogger(__name__)
REQUIRED_PRIVILEGES = set([
    Privilege.can_administer_thoughtspot,
    Privilege.can_manage_data
])


class TSLoadMiddleware:
    """
    """
    def __init__(self, ts):
        self.ts = ts
        # The load server resides on a different port compared to standard ThoughtSpot
        # services. This is because the service tends to carry heavy file-load
        # operations, and having a separate web server creates the needed isolation
        # between standard ThoughtSpot services and tsload operations. By default, this
        # service runs on all nodes of a ThoughtSpot cluster. This provides load
        # distribution to address possible simultaneous loads. The tsload server uses
        # its own load balancer. If an external load balancer is used, the tsload
        # requests must be sticky, and the tsload load balancer should be disabled.
        #
        # To turn off the load balancer, issue the following tscli commands
        #   tscli --adv service add-gflag etl_http_server.etl_http_server etl_server_enable_load_balancer false
        #   tscli --adv service add-gflag etl_http_server.etl_http_server etl_server_always_expose_node_ip true
        #
        #   DEV NOTE
        #     On each public method in this middleware, a keyword argument called
        #     `ignore_node_redirect` which will remove the redirection logic from
        #     further calls to the tsload service api. Since this is handled on a
        #     client-by-client basis with no input from the API itself, we expose it as
        #     a kwarg.
        #
        # Further reading:
        #   https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
        #
        self._cache_fp = APP_DIR / '.cache/tsload-node-redirect-by-cycle-id.json'

    def _cache_node_redirect(self, cycle_id: str, *, node_info: Dict = None) -> Dict[str, Dict]:
        """
        Method is a total hack.
        """
        try:
            with self._cache_fp.open(mode='r') as j:
                cache = json.load(j)
        except FileNotFoundError:
            cache = {}

        # nothing to write, or we should be reading
        if node_info is None:
            return cache

        # write to cache
        now = dt.datetime.utcnow().timestamp()
        cache[cycle_id] = {**node_info, 'load_datetime': now}

        # keep only recent data
        cache = {
            cycle: details
            for cycle, details in cache.items()
            if (now - details['load_datetime']) <= (10 * 86400)  # 10 days
        }

        with self._cache_fp.open(mode='w') as j:
            json.dump(cache, j, indent=4, sort_keys=True)

        return cache

    def _check_for_redirect_auth(self, cycle_id: str) -> None:
        """
        Attempt a login.

        By default, the tsload service API sits behind a load balancer. When we first
        init a new load cycle, the balancer will respond with the proper node (if 
        applicable) to submit file uploads to. If that node is not the main node, then
        we will be required to authorize again.
        """
        cache = self._cache_node_redirect(cycle_id)

        if cycle_id in cache:
            ds = self.ts.api.ts_dataservice
            ds._tsload_node = cache[cycle_id]['host']
            ds._tsload_port = cache[cycle_id]['port']
            log.debug(f'redirecting to: {ds.etl_server_fullpath}')
            ds.load_auth()

    def _check_privileges(self) -> None:
        """
        Determine if the user has necessary Data Manager privileges.
        """
        if not set(self.ts.me.privileges).intersection(REQUIRED_PRIVILEGES):
            raise InsufficientPrivileges(
                user=self.ts.me,
                service='remote TQL',
                required_privileges=', '.join(REQUIRED_PRIVILEGES)
            )

    @validate_arguments(config=dict(arbitrary_types_allowed=True))
    def upload(
        self,
        fd: Union[BufferedIOBase, TextIOWrapper, _TemporaryFileWrapper],
        *,
        database: str,
        table: str,
        schema_: str = 'falcon_default_schema',
        empty_target: bool = True,
        max_ignored_rows: int = 0,
        date_format: str = FMT_TSLOAD_DATE,
        date_time_format: str = FMT_TSLOAD_DATETIME,
        time_format: str = FMT_TSLOAD_TIME,
        skip_second_fraction: bool = False,
        field_separator: str = '|',
        null_value: str = '',
        boolean_representation: str = FMT_TSLOAD_TRUE_FALSE,
        has_header_row: bool = False,
        escape_character: str = '"',
        enclosing_character: str = '"',
        flexible: bool = False,
        # not related to Remote TSLOAD API
        ignore_node_redirect: bool = False,
        http_timeout: int = 60.0
    ) -> List[Dict[str, Any]]:
        """
        Load a file via tsload on a remote server.

        Defaults to tsload command of:
            tsload --source_file <fp>
                   --target_database <target_database>
                   --target_schema 'falcon_default_schema'
                   --target_table <target_table>
                   --max_ignored_rows 0
                   --date_time_format '%Y-%m-%d %H:%M:%S'
                   --field_separator '|'
                   --null_value ''
                   --boolean_representation True_False
                   --escape_character '"'
                   --enclosing_character '"'
                   --empty_target

        For further information on tsload, please refer to:
          https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
          https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
          https://docs.thoughtspot.com/latest/reference/data-importer-ref.html

        Parameters
        ----------
        fp : pathlib.Path
          file to load to thoughtspot

        ignore_node_redirect : bool  [default: False]
          whether or not to ignore node redirection

        **tsload_options

        Returns
        -------
        cycle_id
          unique identifier for this specific file load

        Raises
        ------
        TSLoadServiceUnreachable
          raised when the tsload api service is not reachable
        """
        self._check_privileges()

        flags = {
            'target': {
                'database': database,
                'schema': schema_,
                'table': table
            },
            'format': {
                'field_separator': field_separator,
                'enclosing_character': enclosing_character,
                'escape_character': escape_character,
                'null_value': null_value,
                'date_time': {
                    'date_time_format': date_time_format,
                    'date_format': date_format,
                    'time_format': time_format,
                    'skip_second_fraction': skip_second_fraction
                },
                'boolean': {
                    'true_format': boolean_representation.split('_')[0],
                    'false_format': boolean_representation.split('_')[1]
                },
                'has_header_row': has_header_row,
                'flexible': flexible
            },
            'load_options': {
                'empty_target': empty_target,
                'max_ignored_rows': max_ignored_rows
            }
        }

        try:
            r = self.ts.api.ts_dataservice.load_init(flags, timeout=http_timeout)
        except Exception as e:
            raise TSLoadServiceUnreachable(
                f'[red]something went wrong trying to access tsload service: {e}[/]'
                f'\n\nIf you haven\'t enabled tsload service yet, please find the link '
                f'below further information:'
                f'\nhttps://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html'
                f'\n\nHeres the tsload command for the file you tried to load:'
                f'\n\ntsload --source_file {fd.name} --target_database {database} '
                f'--target_schema {schema_} --target_table {table} '
                f'--max_ignored_rows {max_ignored_rows} --date_format "{FMT_TSLOAD_DATE}" '
                f'--time_format "{FMT_TSLOAD_TIME}" --date_time_format "{FMT_TSLOAD_DATETIME}" '
                f'--field_separator "{field_separator}" --null_value "{null_value}" '
                f'--boolean_representation {boolean_representation} '
                f'--escape_character "{escape_character}" --enclosing_character "{enclosing_character}"'
                + ('--empty_target ' if empty_target else '--noempty_target ')
                + ('--has_header_row ' if has_header_row else '')
                + ('--skip_second_fraction ' if skip_second_fraction else '')
                + ('--flexible' if flexible else ''),
                http_error=e
            )

        data = r.json()
        self._cache_node_redirect(data['cycle_id'], node_info=data.get('node_address', None))

        if not ignore_node_redirect:
            self._check_for_redirect_auth(data['cycle_id'])

        self.ts.api.ts_dataservice.load_start(data['cycle_id'], fd=fd, timeout=http_timeout)
        self.ts.api.ts_dataservice.load_commit(data['cycle_id'])
        return data['cycle_id']

    @validate_arguments
    def status(
        self,
        cycle_id: str,
        *,
        ignore_node_redirect: bool = False,
        wait_for_complete: bool = False
    ) -> Dict[str, Any]:
        """
        Get the status of a previously started data load.

        Parameters
        ----------
        cycle_id : str
          data load to check on

        ignore_node_redirect : bool  [default: False]
          whether or not to ignore node redirection

        wait_for_complete: bool  [default: False]
          poll the load server until it responds with OK or ERROR
        """
        self._check_privileges()

        if not ignore_node_redirect:
            self._check_for_redirect_auth(cycle_id=cycle_id)

        while True:
            r = self.ts.api.ts_dataservice.load_status(cycle_id)
            data = r.json()

            if not wait_for_complete:
                break

            if data['internal_stage'] == 'DONE':
                break
            
            if data['status']['message'] != 'OK':
                break

            log.debug(f'data load status:\n{data}')
            time.sleep(1)

        return data

    # @validate_arguments
    # def bad_records(self, cycle_id: str) -> List[Dict[str, Any]]:
    #     """
    #     """
    #     r = self.ts.api.ts_dataservice.load_params(cycle_id)
    #     params = r.json()
    #     print(params)
    #     raise

    #     r = self.ts.api.ts_dataservice.bad_records(cycle_id)
    #     r.text
