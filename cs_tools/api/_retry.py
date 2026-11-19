from __future__ import annotations

from collections.abc import Callable
from typing import Any
import functools as ft
import logging

import httpx
import tenacity

log = logging.getLogger(__name__)

# EACH WAIT BETWEEN ATTEMPTS HOLDS ONE OF THE TRANSPORT'S CONCURRENCY SLOTS, SO A LONG WAIT
# COLLAPSES THROUGHPUT EXACTLY WHEN THE SERVER IS STRUGGLING. NO WAIT MAY EXCEED THIS.
MAX_WAIT_SECONDS = 30.0

# A RATE LIMIT (429) IS A BUDGET, NOT A FAULT: THE REQUEST SUCCEEDS ONCE THE WINDOW ROLLS OVER,
# SO IT EARNS MORE PATIENCE THAN A GATEWAY ERROR OR A DROPPED CONNECTION.
MAX_ATTEMPTS = 3
MAX_ATTEMPTS_WHEN_RATE_LIMITED = 6

# MARKS A REQUEST WHOSE ENDPOINT CANNOT SAFELY BE SENT TWICE (eg. TML IMPORT).
NON_IDEMPOTENT_HEADER = "x-cs-tools-non-idempotent"

# SAFETY NET FOR THE KNOWN-DANGEROUS ENDPOINTS, IN CASE AN ENDPOINT EVER DROPS ITS MARKER.
# ts_dataservice COVERS THE FALCON DATALOAD CYCLE — RE-SENDING A CHUNK COULD DUPLICATE ROWS.
_NON_IDEMPOTENT_PATH_FRAGMENTS = (
    "metadata/tml/import",
    "metadata/tml/async/import",
    "ts_dataservice/v1/public/loads",
)


def mark_nonidempotent(fn: Callable) -> Callable:
    """Mark an HTTPX endpoint as unsafe to re-send by injecting the non-idempotent header."""

    @ft.wraps(fn)
    def wrapper(self: Any, *a: Any, headers: httpx._types.HeaderTypes | None = None, **kw: Any) -> httpx.Response:
        if headers is None:
            headers = {}

        headers[NON_IDEMPOTENT_HEADER] = "true"  # type: ignore[index]
        return fn(self, *a, headers=headers, **kw)

    return wrapper


def _is_retry_unsafe(request: httpx.Request) -> bool:
    """Determine if re-sending the request risks duplicating work on the server."""
    if NON_IDEMPOTENT_HEADER in request.headers:
        return True

    return any(fragment in str(request.url) for fragment in _NON_IDEMPOTENT_PATH_FRAGMENTS)


def log_on_any_retry(state: tenacity.RetryCallState) -> None:
    """Log a warning when a retry is attempted."""
    assert state.outcome is not None, "Outcome not set before attempting to retry."

    try:
        r: httpx.Response = state.outcome.result()
        r.raise_for_status()

    except httpx.RequestError as e:
        msg = f"{e.__class__.__name__} after {state.seconds_since_start:.2f}s for {e.request.url}"

    except httpx.HTTPStatusError as e:
        msg = f"HTTP {e.response.status_code} for {e.response.url}"

    except Exception as e:
        msg = f"unrecognized {e.__class__.__name__} after {state.seconds_since_start:.2f}s"
        log.debug("Something went wrong.", exc_info=True)

    else:
        msg = "no error, but improper payload"
        log.debug(f"DATA BELOW\n\n{r.text}\n")

    log.warning(f"{msg} on attempt {state.attempt_number}, retrying in {state.upcoming_sleep}s")


def request_errors_unless_importing_tml(exception: BaseException) -> bool:
    """Retry if we hit a transient network error, unless it is a TML Import job."""
    # THE REQUEST NEVER REACHED THE SERVER, SO IT IS ALWAYS SAFE TO SEND AGAIN.
    if isinstance(exception, (httpx.ConnectTimeout, httpx.PoolTimeout)):
        return True

    # THE SERVER MAY HAVE ALREADY PROCESSED THESE, SO ONLY IDEMPOTENT REQUESTS MAY BE RE-SENT.
    ambiguous_transient_exceptions = (
        httpx.TimeoutException,  # ThoughtSpot did not respond in time
        httpx.NetworkError,  # Too many HTTP connections are open to ThoughtSpot
        httpx.RemoteProtocolError,  # The network connectivity to ThoughtSpot has expired, but we sent a request
    )

    if isinstance(exception, ambiguous_transient_exceptions):
        return not _is_retry_unsafe(exception.request)

    # Base case, don't retry.
    return False


def _last_response(state: tenacity.RetryCallState) -> httpx.Response | None:
    """The response the last attempt produced, if it produced one at all."""
    if state.outcome is None or state.outcome.failed:
        return None

    result = state.outcome.result()
    return result if isinstance(result, httpx.Response) else None


def _retry_after_seconds(response: httpx.Response) -> float | None:
    """How long the server asked us to wait, when it said so in seconds."""
    value = response.headers.get("Retry-After")

    if value is None:
        return None

    try:
        seconds = float(value)
    # THE HEADER MAY ALSO CARRY AN HTTP-DATE. THE CLOCK SKEW MATH IS NOT WORTH IT; BACK OFF INSTEAD.
    except ValueError:
        return None

    return seconds if seconds > 0 else None


class wait_retry_after_or_backoff(tenacity.wait.wait_base):
    """Wait as long as a rate-limited response asks, capped; otherwise fall back to backoff."""

    def __init__(self, fallback: tenacity.wait.wait_base, max_wait: float = MAX_WAIT_SECONDS) -> None:
        self.fallback = fallback
        self.max_wait = max_wait

    def __call__(self, retry_state: tenacity.RetryCallState) -> float:
        response = _last_response(retry_state)

        if response is None or response.status_code != httpx.codes.TOO_MANY_REQUESTS:
            return self.fallback(retry_state)

        hinted = _retry_after_seconds(response)

        if hinted is None:
            return self.fallback(retry_state)

        return min(hinted, self.max_wait)


class stop_after_attempts_by_outcome(tenacity.stop.stop_base):
    """Allow more attempts when the last response was a rate limit, fewer for everything else."""

    def __call__(self, retry_state: tenacity.RetryCallState) -> bool:
        response = _last_response(retry_state)

        if response is not None and response.status_code == httpx.codes.TOO_MANY_REQUESTS:
            return retry_state.attempt_number >= MAX_ATTEMPTS_WHEN_RATE_LIMITED

        return retry_state.attempt_number >= MAX_ATTEMPTS


def if_server_is_under_pressure(response: httpx.Response) -> bool:
    """Retry the request if the server signals transient pressure, unless re-sending is unsafe."""
    transient_pressure_statuses = {
        httpx.codes.TOO_MANY_REQUESTS,  # 429
        httpx.codes.SERVICE_UNAVAILABLE,  # 503
        httpx.codes.BAD_GATEWAY,  # 502
        httpx.codes.GATEWAY_TIMEOUT,  # 504
    }

    if response.status_code not in transient_pressure_statuses:
        return False

    # A GATEWAY GIVING UP DOES NOT MEAN THE SERVER STOPPED WORKING ON THE REQUEST.
    return not _is_retry_unsafe(response.request)
