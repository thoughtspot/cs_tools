from typing import Dict, List, BinaryIO
import datetime as dt
import logging
import pathlib
import json

import typer
import httpx

from cs_tools.helpers.secrets import reveal
from cs_tools.util import requires


log = logging.getLogger(__name__)


class TSDataService:
    """
    Services the remote TSLoad and TQL apis.

    For more information on the ts_dataservice APIs, please refer to:
      https://docs.thoughtspot.com/latest/reference/tql-service-api-ref.html
      https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

        # The load server resides on a different port compared to standard ThoughtSpot
        # services. This is because the service tends to carry heavy file-load
        # operations, and having a separate web server creates the needed isolation
        # between standard ThoughtSpot services and tsload operations. By default, this
        # service runs on all nodes of a ThoughtSpot cluster. This provides load
        # distribution to address possible simultaneous loads. The tsload server uses
        # its own load balancer. If an external load balancer is used, the tsload
        # requests must be sticky, and the tsload load balancer should be disabled.
        #
        # To turn off the load balancer, issue this tscli command
        #   tscli --adv service add-gflag etl_http_server.etl_http_server etl_server_enable_load_balancer false
        #
        # Further reading:
        #   https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html
        self._tsload_node = rest_api._config.thoughtspot.fullpath
        self._tsload_port = 8442
        self._tsload_logged_in = False

        app_dir = pathlib.Path(typer.get_app_dir('cs_tools'))
        (app_dir / '.cache').mkdir(parents=True, exist_ok=True)
        self._cache_fp = app_dir / '.cache/cycle-id-nodes.json'

    @property
    def etl_server_fullpath(self) -> str:
        """
        Handle etl_http_server load balancer redirects.
        """
        return f'{self._tsload_node}:{self._tsload_port}/v1/public'

    @requires(software='6.2.1', cloud='*')
    def tokens_static(self) -> httpx.Response:
        """
        Get tokens for static autocomplete.

        Supports building of an interactive remote TQL client.
        """
        r = self.rest_api.request('GET', 'tql/tokens/static', privacy='dataservice')
        return r

    @requires(software='6.2.1', cloud='*')
    def tokens_dynamic(self) -> httpx.Response:
        """
        Get tokens for dynamic autocomplete.

        Supports building of an interactive remote TQL client.
        """
        r = self.rest_api.request('GET', 'tql/tokens/dynamic', privacy='dataservice')
        return r

    @requires(software='6.2.1', cloud='*')
    def query(self, data, *, timeout: float=5.0) -> httpx.Response:
        """
        Run a TQL query.
        """
        r = self.rest_api.request(
                'POST',
                'tql/query',
                privacy='dataservice',
                timeout=timeout,
                json=data,
            )

        return r

    @requires(software='6.2.1', cloud='*')
    def script(self, data) -> httpx.Response:
        """
        Execute a series of queries against TQL.
        """
        r = self.rest_api.request(
                'POST',
                'tql/script',
                privacy='dataservice',
                json=data
            )

        return r

    @requires(software='6.2.1', cloud=None)
    def _load_auth(self) -> httpx.Response:
        """
        Remote tsload service login.
        """
        r = self.rest_api.request(
                'POST',
                f'{self.etl_server_fullpath}/session',
                data={
                    'username': self._config.auth['frontend'].username,
                    'password': reveal(self._config.auth['frontend'].password).decode(),
                }
            )

        self._tsload_logged_in = True
        return r

    @requires(software='6.2.1', cloud=None)
    def load_init(self, data: dict, *, timeout: float=5.0) -> httpx.Response:
        """
        Initialize a tsload session, with options data.
        """
        # NOTE: all options data can be found here
        #   https://docs.thoughtspot.com/software/6.2/tsload-service-api-ref.html#_example_use_of_parameters
        if not self._tsload_logged_in:
            self._load_auth()

        r = self.rest_api.request(
                'POST',
                f'{self.etl_server_fullpath}/loads',
                timeout=timeout,
                json=data
            )

        d = r.json()

        # if we're told to redirect from the load balancer, we'll need to re-auth.
        if d['node_address']:  # != {}, not empty
            self._tsload_logged_in = False
            self._cache(
                cycle_id=d['cycle_id'],
                node=d['node_address']['host'],
                port=d['node_address']['port']
            )

        return r

    @requires(software='6.2.1', cloud=None)
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
            cache = self._cache(cycle_id)
            self._tsload_node = cache[cycle_id]['node']
            self._tsload_port = cache[cycle_id]['port']
        except KeyError:
            # happens when etl_http_server loadbalancer is not running
            pass

        if not self._tsload_logged_in:
            self._load_auth()

        r = self.rest_api.request(
                'POST',
                f'{self.etl_server_fullpath}/loads/{cycle_id}',
                files={'upload-file': fd}
            )

        return r

    @requires(software='6.2.1', cloud=None)
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
            cache = self._cache(cycle_id)
            self._tsload_node = cache[cycle_id]['node']
            self._tsload_port = cache[cycle_id]['port']
        except KeyError:
            # happens when etl_http_server loadbalancer is not running
            pass

        if not self._tsload_logged_in:
            self._load_auth()

        r = self.rest_api.request(
                'POST',
                f'{self.etl_server_fullpath}/loads/{cycle_id}/commit',
            )

        return r

    @requires(software='6.2.1', cloud=None)
    def load_status(self, cycle_id: str) -> httpx.Response:
        """
        Return the status of the dataload for a particular session.

        Parameters
        ----------
        cycle_id : str
          unique identifier of a load cycle
        """
        try:
            cache = self._cache(cycle_id)
            self._tsload_node = cache[cycle_id]['node']
            self._tsload_port = cache[cycle_id]['port']
        except KeyError:
            # happens when etl_http_server loadbalancer is not running
            pass

        if not self._tsload_logged_in:
            self._load_auth()

        r = self.rest_api.request('GET', f'{self.etl_server_fullpath}/loads/{cycle_id}')
        return r

    # Not sure where to put these.. they're attached to the ts data service
    # API, but only in the sense that the api produces predictable output, and
    # not part of the model itself.

    def _cache(self, cycle_id: str, *, node: str=None, port: int=None) -> Dict[str, str]:
        """
        Small local filestore for managing the load balancer re-route.

        Further reading:
        https://docs.thoughtspot.com/latest/admin/loading/load-with-tsload.html#api-workflow
        https://docs.thoughtspot.com/latest/reference/tsload-service-api-ref.html#response-1
        """
        try:
            with self._cache_fp.open(mode='r') as j:
                cache = json.load(j)
        except FileNotFoundError:
            cache = {}

        # read from cache
        if node is None:
            return cache

        # write to cache
        now = dt.datetime.utcnow().timestamp()
        cache[cycle_id] = {'node': node, 'port': port, 'load_datetime': now}

        # keep only recent data
        cache = {
            cycle: details
            for cycle, details in cache.items()
            if (now - details['load_datetime']) <= (10 * 86400)  # 10 days
        }

        with self._cache_fp.open(mode='w') as j:
            json.dump(cache, j, indent=4, sort_keys=True)

        return cache

    @staticmethod
    def _parse_tql_query(table: Dict) -> str:
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
