from __future__ import annotations

from typing import Literal
import functools as ft
import logging
import time

import httpx

from cs_tools.api._utils import scrub_undefined, scrub_sensitive
from cs_tools._version import __version__

log = logging.getLogger(__name__)


class RESTAPIClient:
    """
    Implementation of the REST API v1.
    """

    def __init__(self, ts_url: str, client_version: Literal["V1", "V2"], **client_opts):
        self.client_version = client_version
        client_opts["base_url"] = ts_url
        self.session = httpx.Client(**client_opts)

        # DEV NOTE: @boonhapus 2023/01/08
        #    these are enforced client settings regardless of API call
        #
        #    TIMEOUT = 15 minutes
        #    HEADERS = metadata about requests sent to the ThoughtSpot server
        #
        self.session.timeout = 15 * 60
        self.session.headers.update(
            {
                "x-requested-by": "CS Tools",
                "user-agent": f"cs_tools/{__version__} (+github: thoughtspot/cs_tools)",
            },
        )

        # Expose httpx.session CRUD on our client.
        for verb in ("POST", "GET", "PUT", "DELETE"):
            method_name = verb.lower()
            method = ft.partial(self.request, method_name)
            setattr(self, method_name, method)

    def request(self, method: str, endpoint: str, **request_kw) -> httpx.Response:
        """Make an HTTP request."""
        secure = scrub_sensitive(request_kw)

        log.debug(f">> {method.upper()} to {self.client_version}: {endpoint} with keywords {secure}")

        try:
            r = self.session.request(method, endpoint, **request_kw)

        except httpx.RequestError as e:
            log.warning(f"Could not connect to your ThoughtSpot cluster: {e}")
            log.debug("Something went wrong calling the ThoughtSpot API", exc_info=True)
            raise e from None

        except httpx.HTTPStatusError:
            attempts = 0

            # exponential backoff to 3 attempts (4s, 16s, 64s)
            while r.status_code in (httpx.codes.GATEWAY_TIMEOUT, httpx.codes.BAD_GATEWAY):
                attempts += 1

                if attempts > 3:
                    break

                wait = 4 ** attempts
                log.warning(f"ThoughtSpot timed out on '{method} {endpoint}', waiting {wait}s, see logs for details..")
                log.debug("Full details", exc_info=True)
                time.sleep(wait)
                r = self.session.request(method, endpoint, **request_kw)

        log.debug(f"<< HTTP: {r.status_code}")
        TRACE = 5

        if r.text:
            log.log(TRACE, "<< CONTENT:\n\n%s", r.text)

        if r.is_error:
            log.log(TRACE, ">> HEADERS:\n\n%s", r.request.headers)
            r.raise_for_status()

        return r
