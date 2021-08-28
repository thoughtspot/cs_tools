from typing import Union, Dict, List, Iterator, BinaryIO
import datetime as dt
import logging
import pathlib
import json

import typer
import httpx

from cs_tools.helpers.secrets import reveal
from cs_tools.models._base import APIBase


log = logging.getLogger(__name__)


class TSDataService(APIBase):
    """

    For more information on the ts_dataservice APIs, please refer to:
      https://docs.thoughtspot.com/latest/reference/tql-service-api-ref.html
      https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
    """
    def __init__(self, ts):
        super().__init__(ts)
        # The load server resides on a different port compared to standard ThoughtSpot
        # services. This is because the service tends to carry heavy file-load
        # operations, and having a separate web server creates the needed isolation
        # between standard ThoughtSpot services and tsload operations. By default, this
        # service runs on all nodes of a ThoughtSpot cluster. This provides load
        # distribution to address possible simultaneous loads. The tsload server uses
        # its own load balancer. If an external load balancer is used, the tsload
        # requests must be sticky, and the tsload load balancer should be disabled.
        #
        # Further reading:
        #   https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
        self.tsload_saas_node = ts.config.thoughtspot.host
        self.tsload_saas_port = 8442
        self._tsload_logged_in = False

    @property
    def logged_in(self) -> bool:
        """
        Determine whether or not the user is logged into the dataservice api.
        """
        return self._tsload_logged_in

    @property
    def tql_base_url(self):
        """
        Append to the base URL.
        """
        return f'{super().base_url}/ts_dataservice/v1/public/tql'

    @property
    def tsload_base_url(self):
        """
        Handle location of the ThoughtSpot tsload webserver.
        """
        host = self.tsload_saas_node
        port = self.tsload_saas_port

        if not host.startswith('http'):
            host = f'https://{host}'

        return f'{host}:{port}/ts_dataservice/v1/public'

    def tokens_static(self):
        """

        Supports building of an interactive remote TQL client.
        """
        r = self.get(f'{self.tql_base_url}/tokens/static')
        return r

    def tokens_dynamic(self):
        """

        Supports building of an interactive remote TQL client.
        """
        r = self.get(f'{self.tql_base_url}/tokens/dynamic')
        return r

    def query(self, data, *, stream: bool=False, timeout=5.0) -> Union[httpx.Response, Iterator[httpx.Response]]:
        """
        Run a TQL query.

        This returns an iterator.
        """
        kw = {'json': data, 'timeout': timeout}

        if stream:
            return self.http.stream('POST', f'{self.tql_base_url}/query', **kw)

        return self.post(f'{self.tql_base_url}/query', **kw)

    def script(self, data, *, stream: bool=False) -> Union[httpx.Response, Iterator[httpx.Response]]:
        """
        Execute a series of queries against TQL.

        This returns an iterator.
        """
        if stream:
            return self.http.stream('POST', f'{self.tql_base_url}/script', json=data)

        return self.post(f'{self.tql_base_url}/script', json=data)

    def _load_auth(self) -> httpx.Response:
        """
        Remote tsload service login.
        """
        # TODO
        # should we handle and give warnings for this? [service unreachable]
        #
        # httpx.ConnectError: [WinError 10060] A connection attempt failed because the connected party did not properly
        #                     respond after a period of time, or established connection failed because connected host
        #                     has failed to respond
        auth = {
            'username': self.config.auth['frontend'].username,
            'password': reveal(self.config.auth['frontend'].password).decode(),
        }

        r = self.http.post(f'{self.tsload_base_url}/session', data=auth)

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError('login failed.') from e

        self._tsload_logged_in = True
        return r

    def load_init(self, data: dict, *, timeout: float=5.0) -> httpx.Response:
        """
        Initialize a tsload session, with options data.
        """
        # TODO
        #
        # tsload_params = {
        #     'target': {
        #         'database': None,
        #         'schema': None,
        #         'table': None
        #     },
        #     'format': {
        #         'type': None,
        #         'field_separator': None,
        #         'trailing_field_separator': None,
        #         'enclosing_character': None,
        #         'escape_character': None,
        #         'null_value': None,
        #         'has_header_row': None,
        #         'flexible': None,
        #         'date_time': {
        #             'converted_to_epoch': None,
        #             'date_format': None,
        #             'time_format': None,
        #             'second_fraction_start': None,
        #             'skip_second_fraction': None
        #         },
        #         'boolean': {
        #             'use_bit_values': None,
        #             'true_format': None,
        #             'false_format': None
        #         }
        #     },
        #     'load_options': {
        #         'empty_target': None,
        #         'max_ignored_rows': None
        #     },
        #     'advanced_options': {
        #         'validate_only': None,
        #         'file_target_dir': None
        #     }
        # }
        if not self.logged_in:
            self._load_auth()

        r = self.post(f'{self.tsload_base_url}/loads', json=data, timeout=timeout)

        try:
            data = r.json()
            self._cache_target_node_ip_for_cycle_id(
                mode='w', cycle_id=data['cycle_id'], node=data['node_address']['host'],
                port=data['node_address']['port']
            )
            self._tsload_logged_in = False
        except KeyError:
            pass

        return r

    def load_start(
        self,
        cycle_id: str,
        *,
        fd: BinaryIO
    ) -> httpx.Response:
        """
        Begin loading data in this session.

        This endpoint will return immediately once the file has loaded to the remote
        network. Processing of the dataload may happen concurrently, and thus, this
        function may be called multiple times to paralellize the full data load across
        multiple files.

        Parameters
        ----------
        cycle_id : str
          unique identifier of a load cycle

        fd : BinaryIO
          a file-like object to load to Falcon
        """
        try:
            cache = self._cache_target_node_ip_for_cycle_id(mode='r')
            self.tsload_saas_node = cache[cycle_id]['node']
            self.tsload_saas_port = cache[cycle_id]['port']
        except KeyError:
            # if the etl_http_server loadbalancer is not running, we'll hit a KeyError
            #
            # aka:
            #   tscli --adv service add-gflag etl_http_server.etl_http_server etl_server_enable_load_balancer false
            pass

        if not self.logged_in:
            self._load_auth()

        r = self.post(f'{self.tsload_base_url}/loads/{cycle_id}', files={'upload-file': fd})
        return r

    def load_commit(self, cycle_id: str) -> httpx.Response:
        """
        Commits currently ingested data to Falcon in this session.

        The commit will happen asynchronously, this method returns immediately.

        Parameters
        ----------
        cycle_id : str
          unique identifier of a load cycle
        """
        try:
            cache = self._cache_target_node_ip_for_cycle_id(mode='r')
            self.tsload_saas_node = cache[cycle_id]['node']
            self.tsload_saas_port = cache[cycle_id]['port']
        except KeyError:
            pass

        if not self.logged_in:
            self._load_auth()

        r = self.post(f'{self.tsload_base_url}/loads/{cycle_id}/commit')
        return r

    def load_status(self, cycle_id: str) -> httpx.Response:
        """
        Return the status of the dataload for a particular session.

        Parameters
        ----------
        cycle_id : str
          unique identifier of a load cycle
        """
        try:
            cache = self._cache_target_node_ip_for_cycle_id(mode='r')
            self.tsload_saas_node = cache[cycle_id]['node']
            self.tsload_saas_port = cache[cycle_id]['port']
        except KeyError:
            pass

        if not self.logged_in:
            self._load_auth()

        r = self.get(f'{self.tsload_base_url}/loads/{cycle_id}')
        return r

    # Not sure where to put these.. they're attached to the ts data service
    # API, but only in the sense that the api produces predictable output, and
    # not part of the model itself.

    @staticmethod
    def _cache_target_node_ip_for_cycle_id(
        *,
        mode: str='w',
        cycle_id: str=None,
        node: str=None,
        port: int=None
    ):
        """
        Small local filestore for managing the load balancer re-route.

        Further reading:
        https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html#api-workflow
        https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html#response-1
        """
        cache = {}
        app_dir = pathlib.Path(typer.get_app_dir('cs_tools'))
        (app_dir / '.cache').mkdir(parents=True, exist_ok=True)
        FILE_CACHE = app_dir / '.cache/cycle-id-nodes.json'

        if mode == 'w' and (cycle_id is None or node is None):
            raise ValueError(
                f'cycle_id and node must be valid values, got: {cycle_id}, {node}'
            )

        if FILE_CACHE.exists():
            with FILE_CACHE.open(mode='r') as j:
                cache = json.load(j)

        if mode == 'r':
            return cache

        now = dt.datetime.utcnow().timestamp()
        cache[cycle_id] = {'node': node, 'port': port, 'load_datetime': now}

        # keep only recent data
        cache = {
            cycle: details
            for cycle, details in cache.items()
            if (now - details['load_datetime']) <= (10 * 86400)  # 10 days
        }

        with FILE_CACHE.open(mode='w') as j:
            json.dump(cache, j, indent=4, sort_keys=True)

        return cache

    @staticmethod
    def _parse_tql_query(table: dict) -> str:
        header  = '|'.join(h['name'] for h in table['headers'])
        divider = '-' * len(header)

        try:
            records = '\n'.join('|'.join(r['v']) for r in table['rows'])
        except KeyError:
            records = ''

        return f'[magenta]{header}\n{divider}\n{records}[/]'

    @staticmethod
    def _parse_api_messages(messages: List[str]) -> str:
        messages_ = []

        for msg_data in messages:
            level = msg_data['type']
            text = msg_data['value'].strip()

            if level == 'ERROR':
                color = 'red'

            if level == 'WARNING':
                color = 'yellow'

            if level == 'INFO':
                color = 'white'

            if text == 'Statement executed successfully.':
                color = 'green'

            messages_.append(f'[{color}]{text}[/]')

        return '\n'.join(messages_)

    @staticmethod
    def _parse_tsload_status(status: Dict) -> str:
        if status.get('status', {}).get('code', False) == 'LOAD_FAILED':
            msg = (
                f'\nCycle ID: {status["cycle_id"]}'
                f'\nStage: {status["internal_stage"]}'
                f'\nStatus: {status["status"]["code"]}'
                f'\n[red]{status["status"]["message"]}[/]'
                f'\n[red]{status["parsing_errors"]}[/]' if 'parsing_errors' in status else ''
            )
        else:
            msg = (
                f'\nCycle ID: {status["cycle_id"]}'
                f'\nStage: [green]{status["internal_stage"]}[/]'
                f'\nRows written: {status["rows_written"]}'
                f'\nIgnored rows: {status["ignored_row_count"]}'
            )

        return msg
