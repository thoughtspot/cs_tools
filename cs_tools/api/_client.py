from __future__ import annotations

from typing import Literal
import datetime as dt
import functools as ft
import logging

import httpx

from cs_tools import __version__
from cs_tools.api import _utils
from cs_tools.api._rest_api_v1 import RESTAPIv1
from cs_tools.api._rest_api_v2 import RESTAPIv2

log = logging.getLogger(__name__)
_CALLOSUM_DEFAULT_TIMEOUT_SECONDS = 60 * 5


class RESTAPIClient:
    """
    This a coordinator for the V1 and V2 implementations.
    """

    def __init__(self, ts_url: str, *, timeout: float = _CALLOSUM_DEFAULT_TIMEOUT_SECONDS, **client_opts):
        if base_url := client_opts.get("base_url", None):
            log.warning(f"base_url '{base_url}' was provided to ThoughtSpot REST API client, overriding with {ts_url}")

        if "headers" not in client_opts:
            client_opts["headers"] = {}

        # ThoughtSpot looks for and logs this item on incoming requests
        client_opts["headers"]["x-requested-by"] = "CS Tools"

        # Metadata about requests coming from this client
        client_opts["headers"]["user-agent"] = f"cs_tools/{__version__} (+github: thoughtspot/cs_tools)"

        if "event_hooks" not in client_opts:
            client_opts["event_hooks"] = {"request": [], "response": []}

        client_opts["event_hooks"]["request"].append(self.__before_request__)
        client_opts["event_hooks"]["response"].append(self.__after_response__)

        self._session = httpx.Client(base_url=ts_url, timeout=timeout, **client_opts)
        self._v1_endpoints = RESTAPIv1(api_client=self)
        self._v2_endpoints = RESTAPIv2(api_client=self)
        self._setup_session_class_proxying()

    def _setup_session_class_proxying(self) -> None:
        """Proxy httpx.Session CRUD operations on our client."""
        self.post = ft.partial(self.request, "POST")
        self.get = ft.partial(self.request, "GET")
        self.put = ft.partial(self.request, "PUT")
        self.delete = ft.partial(self.request, "DELETE")

    def __before_request__(self, request: httpx.Request) -> None:
        """
        Called after a request is fully prepared, but before it is sent to the network.

        Passed the request instance.

        Further reading:
            https://www.python-httpx.org/advanced/#event-hooks
        """
        now = dt.datetime.now(tz=dt.timezone.utc)
        request.headers["cs-tools-request-start-utc-timestamp"] = now.isoformat()

        log_msg = (
            f">>> [{now:%H:%M:%S}] HTTP {request.method} -> {request.url.path}"
            f"\n\t=== HEADERS ===\n{request.headers}"
        )

        if request.url.params:
            log_msg += f"\n\t===  PARAMS ===\n{_utils.obfuscate_sensitive_data(request.url.params)}"

        if content := request.content.decode():
            log_msg += f"\n\t===    DATA ===\n{_utils.obfuscate_sensitive_data(httpx.QueryParams(content))}"

        log.debug(f"{log_msg}\n")

    def request(self, method: Literal["POST", "GET", "PUT", "DELETE"], url: str, **kwargs) -> httpx.Response:
        """Proxy httpx.Session base method on our client."""
        # DEV NOTE: @boonhapus, 2024/02/15
        # If we want to make the CS Tools HTTP client asyncio-friendly, all we need to do is swap the this/before/after
        # request methods for async counterparts.
        return self._session.request(method, url, **kwargs)

    def __after_response__(self, response: httpx.Response) -> None:
        """
        Called after the response has been fetched from the network, but before it is returned to the caller.

        Passed the response instance.

        Response event hooks are called before determining if the response body should be read or not.

        Further reading:
            https://www.python-httpx.org/advanced/#event-hooks
        """
        now = dt.datetime.now(tz=dt.timezone.utc)
        response.headers["cs-tools-response-receive-utc-timestamp"] = now.isoformat()

        if utc_requested_at := response.request.headers.get("cs-tools-request-start-utc-timestamp", None):
            elapsed = f"({(now - dt.datetime.fromisoformat(utc_requested_at)).total_seconds()}s)"
        else:
            elapsed = ""

        log_msg = f"<<< [{now:%H:%M:%S}] HTTP {response.status_code} <- {response.request.url.path} {elapsed}"

        if response.status_code >= 400:
            response.read()
            log_msg += f"\n{response.text}\n"

        log.debug(log_msg)

    @property
    def v1(self) -> RESTAPIv1:
        """ThoughtSpot REST API V1 Handling."""
        return self._v1_endpoints

    @property
    def v2(self) -> RESTAPIv2:
        """ThoughtSpot REST API V2 Handling."""
        return self._v2_endpoints
