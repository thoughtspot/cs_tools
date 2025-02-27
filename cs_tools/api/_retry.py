from __future__ import annotations

import logging

import httpx
import tenacity

log = logging.getLogger(__name__)


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
    """Retry if we hit a timeout/read error, unless it is a TML Import job."""
    httpx_request_exceptions = (
        httpx.ReadTimeout,  # ThoughtSpot did not respond in time
        httpx.NetworkError,  # Too many HTTP connections are open to ThoughtSpot
        httpx.RemoteProtocolError,  # The network connectivity to ThoughtSpot has expired, but we sent a request
    )

    if isinstance(exception, httpx_request_exceptions):
        return "metadata/tml/import" in str(exception.request.url)

    # Base case, don't retry.
    return False


def if_server_is_under_pressure(response: httpx.Response) -> bool:
    """Retry the request if we hit a server timeout."""
    return response.status_code in {httpx.codes.GATEWAY_TIMEOUT, httpx.codes.BAD_GATEWAY}
