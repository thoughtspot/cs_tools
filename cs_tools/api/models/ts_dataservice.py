from typing import Any, Union
from io import BufferedIOBase
import logging

from pydantic import validate_arguments
import httpx

from cs_tools.util import reveal


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
        self._tsload_node = rest_api._config.thoughtspot.fullpath
        self._tsload_port = 8442

    @property
    def etl_server_fullpath(self) -> str:
        """
        Handle etl_http_server load balancer redirects.
        """
        host = self._tsload_node

        if not host.startswith('http'):
            host = f'https://{host}'

        return f'{host}:{self._tsload_port}/ts_dataservice/v1/public'

    def tokens_static(self) -> httpx.Response:
        """
        Get tokens for static autocomplete.

        Supports building of an interactive remote TQL client.
        """
        r = self.rest_api.request('GET', 'tql/tokens/static', privacy='dataservice')
        return r

    def tokens_dynamic(self) -> httpx.Response:
        """
        Get tokens for dynamic autocomplete.

        Supports building of an interactive remote TQL client.
        """
        r = self.rest_api.request('GET', 'tql/tokens/dynamic', privacy='dataservice')
        return r

    @validate_arguments
    def query(self, data: Any, *, timeout: float = 15.0) -> httpx.Response:
        """
        Run a TQL query.

        Further reading on what can be passed to `data`:
        https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_inputoutput_structure
        https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_request_body
        """
        r = self.rest_api.request(
                'POST',
                'tql/query',
                privacy='dataservice',
                timeout=timeout,
                json=data,
            )

        return r

    @validate_arguments
    def script(self, data: Any, *, timeout: float = 15.0) -> httpx.Response:
        """
        Execute a series of queries against TQL.

        Further reading on what can be passed to `data`:
        https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_inputoutput_structure
        https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_request_body_2
        """
        r = self.rest_api.request(
                'POST',
                'tql/script',
                privacy='dataservice',
                timeout=timeout,
                json=data
            )

        return r

    def load_auth(self) -> httpx.Response:
        """
        Remote tsload service login.
        """
        r = self.rest_api.request(
                'POST',
                f'{self.etl_server_fullpath}/session',
                data={
                    'username': self.rest_api._config.auth['frontend'].username,
                    'password': reveal(self.rest_api._config.auth['frontend'].password).decode(),
                }
            )

        return r

    @validate_arguments
    def load_init(self, data: Any, *, timeout: float = 15.0) -> httpx.Response:
        """
        Initialize a tsload session, with options data.
        """
        # NOTE: all options data can be found here
        #   https://docs.thoughtspot.com/software/6.2/tsload-service-api-ref.html#_example_use_of_parameters
        r = self.rest_api.request(
                'POST',
                f'{self.etl_server_fullpath}/loads',
                timeout=timeout,
                json=data
            )

        return r

    @validate_arguments(config={'arbitrary_types_allowed': True})
    def load_start(
        self,
        cycle_id: str,
        *,
        fd: Union[BufferedIOBase, Any],
        timeout: int = 60.0
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
        r = self.rest_api.request(
                'POST',
                f'{self.etl_server_fullpath}/loads/{cycle_id}',
                timeout=timeout,
                files={'upload-file': fd},
            )

        return r

    @validate_arguments
    def load_commit(self, cycle_id: str) -> httpx.Response:
        """
        Commits currently ingested data to Falcon in this session.

        The commit will happen asynchronously, this method returns immediately.

        Parameters
        ----------
        cycle_id : str
          unique identifier of a load cycle
        """
        r = self.rest_api.request(
                'POST',
                f'{self.etl_server_fullpath}/loads/{cycle_id}/commit',
            )

        return r

    @validate_arguments
    def load_status(self, cycle_id: str) -> httpx.Response:
        """
        Return the status of the dataload for a particular session.

        Parameters
        ----------
        cycle_id : str
          unique identifier of a load cycle
        """
        r = self.rest_api.request('GET', f'{self.etl_server_fullpath}/loads/{cycle_id}')

        return r

    @validate_arguments
    def load_params(self, cycle_id: str) -> httpx.Response:
        """
        Return the status of the dataload for a particular session.

        Parameters
        ----------
        cycle_id : str
          unique identifier of a load cycle
        """
        r = self.rest_api.request(
            'GET',
            f'{self.etl_server_fullpath}/loads/{cycle_id}/input_summary'
        )

        return r

    @validate_arguments
    def bad_records(self, cycle_id: str) -> httpx.Response:
        """
        Return the status of the dataload for a particular session.

        Parameters
        ----------
        cycle_id : str
          unique identifier of a load cycle
        """
        r = self.rest_api.request(
                'GET',
                f'{self.etl_server_fullpath}/loads/{cycle_id}/bad_records_file'
            )
        return r
