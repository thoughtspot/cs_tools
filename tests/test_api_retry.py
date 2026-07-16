"""
Specification for the CS Tools HTTP retry policy.

cs_tools/api/_retry.py decides which failures are safe to retry. The rules:

- Errors raised before the request ever reaches ThoughtSpot (connect/pool
  timeouts) are always safe to retry.
- Transient errors raised after the request was sent (read timeouts, dropped
  connections) are ambiguous — the server may have already processed the
  request — so they are retried only for endpoints that are safe to re-send.
- Server-pressure statuses (429/502/503/504) follow the same idempotency rule:
  a gateway giving up does not mean the server stopped working on the request.
- Non-idempotent endpoints (TML import, Falcon data loads) are never re-sent;
  a duplicate send can create duplicate customer content.
- Waits between attempts are short, jittered, and capped. Each wait is slept
  while holding one of the transport's concurrency slots, so long waits would
  collapse throughput exactly when the server is struggling.
"""

from __future__ import annotations

from cs_tools.api import _retry
from cs_tools.api.client import RESTAPIClient
import httpx
import pytest
import tenacity

ANY_CLUSTER = "https://customer.thoughtspot.cloud"

# ENDPOINTS WHOSE REQUESTS ARE SAFE TO RE-SEND. MOST OF THE API SURFACE IS
# SEMANTICALLY READ-ONLY (POST-as-search), SO A RE-SENT REQUEST IS HARMLESS.
RETRY_SAFE_ENDPOINTS = [
    "api/rest/2.0/metadata/search",
    "api/rest/2.0/users/search",
    "api/rest/2.0/metadata/tml/export",
    "callosum/v1/tspublic/v1/security/metadata/permissions",
]

# NON-IDEMPOTENT ENDPOINTS. A TIMED-OUT REQUEST MAY STILL HAVE BEEN APPLIED
# SERVER-SIDE, SO RE-SENDING IT CAN DUPLICATE CUSTOMER CONTENT.
RETRY_UNSAFE_ENDPOINTS = [
    "api/rest/2.0/metadata/tml/import",
    "api/rest/2.0/metadata/tml/async/import",
    "ts_dataservice/v1/public/loads/fake-cycle-id",
]

# ERRORS WHERE THE SERVER MAY HAVE ALREADY PROCESSED THE REQUEST. RETRYING IS
# ONLY SAFE IF THE ENDPOINT IS IDEMPOTENT.
AMBIGUOUS_TRANSIENT_ERRORS = [
    httpx.ReadTimeout,
    httpx.ReadError,
    httpx.RemoteProtocolError,
]


def make_request(endpoint: str) -> httpx.Request:
    return httpx.Request("POST", f"{ANY_CLUSTER}/{endpoint}")


def make_error(error_type: type[httpx.TransportError], endpoint: str) -> httpx.TransportError:
    return error_type("transient network blip", request=make_request(endpoint))


def make_response(status_code: int, endpoint: str) -> httpx.Response:
    return httpx.Response(status_code=status_code, request=make_request(endpoint))


class TestTransientErrorPredicate:
    """Spec for _retry.request_errors_unless_importing_tml (retry on exception)."""

    @pytest.mark.parametrize("error_type", AMBIGUOUS_TRANSIENT_ERRORS)
    @pytest.mark.parametrize("endpoint", RETRY_SAFE_ENDPOINTS)
    def test_transient_errors_are_retried_on_retry_safe_endpoints(self, error_type, endpoint):
        error = make_error(error_type, endpoint)
        assert _retry.request_errors_unless_importing_tml(error) is True

    @pytest.mark.parametrize("error_type", AMBIGUOUS_TRANSIENT_ERRORS)
    @pytest.mark.parametrize("endpoint", RETRY_UNSAFE_ENDPOINTS)
    def test_ambiguous_errors_are_never_retried_on_retry_unsafe_endpoints(self, error_type, endpoint):
        error = make_error(error_type, endpoint)
        assert _retry.request_errors_unless_importing_tml(error) is False

    @pytest.mark.parametrize("endpoint", RETRY_SAFE_ENDPOINTS + RETRY_UNSAFE_ENDPOINTS)
    def test_connect_timeout_is_retried_everywhere(self, endpoint):
        # A ConnectTimeout MEANS THE REQUEST NEVER REACHED THE SERVER, SO THERE
        # IS NO IDEMPOTENCY CONCERN — SAFE TO RETRY EVEN FOR TML IMPORT.
        error = make_error(httpx.ConnectTimeout, endpoint)
        assert _retry.request_errors_unless_importing_tml(error) is True

    @pytest.mark.parametrize("endpoint", RETRY_SAFE_ENDPOINTS)
    def test_connect_errors_are_retried(self, endpoint):
        error = make_error(httpx.ConnectError, endpoint)
        assert _retry.request_errors_unless_importing_tml(error) is True

    @pytest.mark.parametrize(
        "error_type",
        [
            httpx.LocalProtocolError,  # WE BUILT A BAD REQUEST — RETRYING CANNOT HELP
            httpx.UnsupportedProtocol,  # CONFIGURATION ERROR — RETRYING CANNOT HELP
            httpx.TooManyRedirects,  # SERVER MISCONFIGURATION — RETRYING CANNOT HELP
        ],
    )
    def test_non_transient_errors_are_never_retried(self, error_type):
        error = make_error(error_type, "api/rest/2.0/metadata/search")
        assert _retry.request_errors_unless_importing_tml(error) is False


class TestServerPressurePredicate:
    """Spec for _retry.if_server_is_under_pressure (retry on response status)."""

    @pytest.mark.parametrize(
        "status_code",
        [
            httpx.codes.BAD_GATEWAY,  # 502
            httpx.codes.GATEWAY_TIMEOUT,  # 504
            httpx.codes.TOO_MANY_REQUESTS,  # 429
            httpx.codes.SERVICE_UNAVAILABLE,  # 503
        ],
    )
    @pytest.mark.parametrize("endpoint", RETRY_SAFE_ENDPOINTS)
    def test_pressure_statuses_are_retried_on_retry_safe_endpoints(self, status_code, endpoint):
        response = make_response(status_code, endpoint)
        assert _retry.if_server_is_under_pressure(response) is True

    @pytest.mark.parametrize(
        "status_code",
        [
            httpx.codes.BAD_GATEWAY,  # 502
            httpx.codes.GATEWAY_TIMEOUT,  # 504
        ],
    )
    @pytest.mark.parametrize("endpoint", RETRY_UNSAFE_ENDPOINTS)
    def test_ambiguous_pressure_statuses_are_never_retried_on_retry_unsafe_endpoints(self, status_code, endpoint):
        # A 502/504 MEANS A GATEWAY GAVE UP WAITING — THE SERVER MAY STILL
        # COMPLETE THE REQUEST. SAME DUPLICATION HAZARD AS A ReadTimeout.
        response = make_response(status_code, endpoint)
        assert _retry.if_server_is_under_pressure(response) is False

    @pytest.mark.parametrize("status_code", [200, 201, 204, 400, 401, 403, 404, 500])
    def test_ordinary_statuses_are_not_retried(self, status_code):
        # 4xx ARE CALLER ERRORS AND 500 IS TYPICALLY A REAL SERVER FAULT WITH A
        # DIAGNOSTIC BODY — BLINDLY RETRYING THEM HIDES THE ACTUAL PROBLEM.
        response = make_response(status_code, "api/rest/2.0/metadata/search")
        assert _retry.if_server_is_under_pressure(response) is False


class TestBackoffPolicy:
    """Spec for the retry policy RESTAPIClient wires into its transport."""

    @pytest.fixture(scope="class")
    @staticmethod
    def retry_policy() -> tenacity.AsyncRetrying:
        client = RESTAPIClient(base_url=ANY_CLUSTER)
        return client._transport.retrier  # type: ignore[union-attr]

    @staticmethod
    def wait_before_attempt(policy: tenacity.AsyncRetrying, attempt_number: int) -> float:
        state = tenacity.RetryCallState(retry_object=policy, fn=None, args=(), kwargs={})
        state.attempt_number = attempt_number
        return policy.wait(state)

    def test_first_retry_is_prompt(self, retry_policy):
        # TRANSIENT BLIPS RESOLVE IN MILLISECONDS-TO-SECONDS.
        assert self.wait_before_attempt(retry_policy, attempt_number=1) <= 5.0

    @pytest.mark.parametrize("attempt_number", [1, 2, 3, 4, 5])
    def test_backoff_is_capped(self, retry_policy, attempt_number):
        assert self.wait_before_attempt(retry_policy, attempt_number) <= 30.0

    def test_gives_up_eventually(self, retry_policy):
        state = tenacity.RetryCallState(retry_object=retry_policy, fn=None, args=(), kwargs={})
        state.attempt_number = 10
        assert retry_policy.stop(state) is True
