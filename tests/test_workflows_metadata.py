"""
Behavioral spec for cs_tools.api.workflows.metadata.fetch.

Drives the real fetch() through a production RESTAPIClient wired to an
in-memory httpx.MockTransport (via CachedRetryTransport's wrapped_transport
seam). No network access occurs.

Pins the properties customers depend on:

  1. fetch bounds the number of identifiers per metadata/search request,
     re-batching however the caller happened to group them. This keeps a
     single wide table (hundreds of columns) from becoming one giant, slow
     request, and keeps thousands of single objects from becoming thousands
     of requests.

  2. A single failing batch does not cancel its siblings. fetch returns the
     rows it could gather and reports the batches it could not, instead of
     aborting the whole phase.

  3. Failures that are NOT transport failures still propagate. Tolerating a
     dropped request must not silently swallow a bug.

  4. Console reporting of failures is capped. A failure storm must not bury
     the progress display under one ERROR line per failed batch.
"""

from __future__ import annotations

from typing import Callable, Union
import asyncio
import json
import logging
import math

from cs_tools.api.client import RESTAPIClient
from cs_tools.api.workflows import metadata as metadata_workflow
import awesomeversion
import httpx
import pytest

ANY_CLUSTER = "https://customer.thoughtspot.cloud"

# THE MOST IDENTIFIERS fetch SHOULD PLACE IN A SINGLE metadata/search REQUEST.
# MIRRORS THE EXISTING PRECEDENT IN client.v1_security_metadata_permissions (n=25).
EXPECTED_MAX_PER_REQUEST = 25


class RecordingServer:
    """In-memory server that records requests and answers by a per-request rule."""

    def __init__(self, respond: Callable[[httpx.Request], Union[int, Exception]]):
        self._respond = respond
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        outcome = self._respond(request)

        if isinstance(outcome, Exception):
            raise outcome

        return httpx.Response(status_code=outcome, json=[{"metadata_id": "OK"}])

    def sent_identifiers(self) -> list[list[str]]:
        """The identifier list carried by each recorded metadata/search request."""
        batches: list[list[str]] = []

        for request in self.requests:
            payload = json.loads(request.content)
            batches.append([m["identifier"] for m in payload["metadata"]])

        return batches


def make_client(server: RecordingServer) -> RESTAPIClient:
    """Build a production-configured client against the server, with retry sleeps skipped."""
    client = RESTAPIClient(base_url=ANY_CLUSTER, wrapped_transport=httpx.MockTransport(server))

    async def do_not_sleep(seconds: float) -> None:  # noqa: ARG001
        return None

    client._transport.retrier.sleep = do_not_sleep  # type: ignore[union-attr]
    return client


def fails_on(marker: bytes, error: Exception) -> Callable[[httpx.Request], Union[int, Exception]]:
    """Answer 200, except for requests carrying the marker."""

    def respond(request: httpx.Request) -> Union[int, Exception]:
        return error if marker in request.content else 200

    return respond


def test_a_wide_identifier_list_is_split_into_bounded_requests():
    # ONE TABLE'S WORTH OF COLUMNS, GROUPED AS THE CALLER DOES IT (a single list),
    # MUST NOT BECOME ONE ENORMOUS metadata/search.
    server = RecordingServer(respond=lambda _: 200)
    guids = [f"col-{i}" for i in range(60)]

    async def scenario() -> None:
        client = make_client(server)
        await metadata_workflow.fetch(
            typed_guids={"LOGICAL_COLUMN": [guids]},
            include_dependent_objects=True,
            dependent_objects_record_size=-1,
            http=client,
        )

    asyncio.run(scenario())

    batches = server.sent_identifiers()
    assert all(len(b) <= EXPECTED_MAX_PER_REQUEST for b in batches), batches
    assert len(batches) == math.ceil(len(guids) / EXPECTED_MAX_PER_REQUEST)
    # EVERY IDENTIFIER SENT, EXACTLY ONCE, IN ORDER.
    assert [g for batch in batches for g in batch] == guids


def test_a_many_single_objects_are_coalesced_into_bounded_requests():
    # THOUSANDS OF SINGLE-GUID OBJECTS MUST NOT BECOME THOUSANDS OF REQUESTS.
    server = RecordingServer(respond=lambda _: 200)
    guids = {f"tbl-{i}" for i in range(60)}

    async def scenario() -> None:
        client = make_client(server)
        await metadata_workflow.fetch(
            typed_guids={"LOGICAL_TABLE": guids},
            include_details=True,
            http=client,
        )

    asyncio.run(scenario())

    batches = server.sent_identifiers()
    assert all(len(b) <= EXPECTED_MAX_PER_REQUEST for b in batches), batches
    assert len(batches) == math.ceil(len(guids) / EXPECTED_MAX_PER_REQUEST)
    # EVERY IDENTIFIER SENT, EXACTLY ONCE.
    sent = [g for batch in batches for g in batch]
    assert len(sent) == len(guids)
    assert set(sent) == guids


def test_c_a_failing_batch_does_not_abort_the_phase():
    # DEPENDENTS CANNOT BE PAGINATED, SO A REQUEST CAN ALWAYS EXCEED THE READ TIMEOUT.
    # ONE DROPPED BATCH MUST NOT COST THE ENTIRE ~25 MINUTE EXTRACT.
    server = RecordingServer(respond=fails_on(b"BOOM", httpx.ReadTimeout("simulated slow endpoint")))
    good = [f"good-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]
    bad = [f"BOOM-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]

    async def scenario() -> list:
        client = make_client(server)
        return await metadata_workflow.fetch(
            typed_guids={"LOGICAL_COLUMN": [good, bad]},
            include_dependent_objects=True,
            dependent_objects_record_size=-1,
            http=client,
        )

    rows = asyncio.run(scenario())

    # THE SURVIVING BATCH'S ROWS COME BACK RATHER THAN BEING DISCARDED.
    assert rows == [{"metadata_id": "OK"}]


def test_c_a_failing_batch_does_not_cancel_its_siblings():
    # THE FAIL-FAST TaskGroup USED TO CANCEL IN-FLIGHT *AND* NOT-YET-STARTED BATCHES.
    # EVERY HEALTHY BATCH MUST STILL BE ATTEMPTED AND RETURNED.
    server = RecordingServer(respond=fails_on(b"BOOM", httpx.ReadError("simulated dropped response")))
    before = [f"before-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]
    bad = [f"BOOM-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]
    after = [f"after-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]

    async def scenario() -> list:
        client = make_client(server)
        return await metadata_workflow.fetch(
            typed_guids={"LOGICAL_COLUMN": [before, bad, after]},
            include_dependent_objects=True,
            dependent_objects_record_size=-1,
            http=client,
        )

    rows = asyncio.run(scenario())

    assert len(rows) == 2, "both healthy batches should have survived the failing one"

    attempted = {g for batch in server.sent_identifiers() for g in batch}
    assert set(before) <= attempted
    assert set(after) <= attempted


def test_c_failed_batches_are_reported_to_the_caller():
    # A PARTIAL EXTRACT IS ONLY ACCEPTABLE IF THE CALLER CAN SAY EXACTLY WHAT IS MISSING.
    server = RecordingServer(respond=fails_on(b"BOOM", httpx.ReadTimeout("simulated slow endpoint")))
    good = [f"good-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]
    bad = [f"BOOM-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]
    failures: list[metadata_workflow.FetchFailure] = []

    async def scenario() -> None:
        client = make_client(server)
        await metadata_workflow.fetch(
            typed_guids={"LOGICAL_COLUMN": [good, bad]},
            include_dependent_objects=True,
            dependent_objects_record_size=-1,
            failures=failures,
            http=client,
        )

    asyncio.run(scenario())

    assert len(failures) == 1
    assert failures[0].metadata_type == "LOGICAL_COLUMN"
    assert list(failures[0].identifiers) == bad
    assert isinstance(failures[0].error, httpx.HTTPError)


def test_c_a_healthy_run_reports_no_failures():
    # THE COLLECTOR MUST STAY EMPTY WHEN NOTHING GOES WRONG -- OTHERWISE EVERY RUN
    # WOULD TRIP THE PARTIAL-EXTRACT GUARD.
    server = RecordingServer(respond=lambda _: 200)
    failures: list[metadata_workflow.FetchFailure] = []

    async def scenario() -> list:
        client = make_client(server)
        return await metadata_workflow.fetch(
            typed_guids={"LOGICAL_COLUMN": [[f"col-{i}" for i in range(60)]]},
            failures=failures,
            http=client,
        )

    rows = asyncio.run(scenario())

    assert failures == []
    assert len(rows) == 3


def test_c_an_error_status_is_treated_as_a_failed_batch():
    # A 4xx/5xx THAT SURVIVES THE RETRY POLICY IS A MISSING BATCH, NOT A CRASH.
    server = RecordingServer(respond=lambda request: 500 if b"BOOM" in request.content else 200)
    good = [f"good-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]
    bad = [f"BOOM-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]
    failures: list[metadata_workflow.FetchFailure] = []

    async def scenario() -> list:
        client = make_client(server)
        return await metadata_workflow.fetch(
            typed_guids={"LOGICAL_COLUMN": [good, bad]},
            failures=failures,
            http=client,
        )

    rows = asyncio.run(scenario())

    assert rows == [{"metadata_id": "OK"}]
    assert len(failures) == 1
    assert list(failures[0].identifiers) == bad


def test_c_exhausted_server_pressure_retries_are_a_failed_batch_not_a_crash():
    # A SERVER STUCK RETURNING 429/502/503/504 EXHAUSTS THE RESULT-BASED RETRY POLICY, WHICH
    # SURFACES AS tenacity.RetryError (NOT AN httpx ERROR -- reraise=True ONLY COVERS EXCEPTIONS).
    # THAT IS STILL "THE SERVER COULD NOT ANSWER", SO IT MUST BECOME A REPORTED GAP, NOT A CRASH.
    server = RecordingServer(respond=lambda request: 429 if b"BOOM" in request.content else 200)
    good = [f"good-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]
    bad = [f"BOOM-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]
    failures: list[metadata_workflow.FetchFailure] = []

    async def scenario() -> list:
        client = make_client(server)
        return await metadata_workflow.fetch(
            typed_guids={"LOGICAL_COLUMN": [good, bad]},
            failures=failures,
            http=client,
        )

    rows = asyncio.run(scenario())

    assert rows == [{"metadata_id": "OK"}]
    assert len(failures) == 1
    assert list(failures[0].identifiers) == bad
    # THE FAILURE IS RECORDED AS THE UNDERLYING STATUS ERROR, NOT AN OPAQUE RetryError.
    assert isinstance(failures[0].error, httpx.HTTPStatusError)
    assert failures[0].error.response.status_code == 429
    # THE RETRY POLICY STILL RAN ITS COURSE BEFORE THE BATCH WAS DECLARED FAILED.
    assert sum(b"BOOM" in r.content for r in server.requests) == 3


def test_c_a_failure_storm_does_not_flood_the_console(caplog):
    # A SERVER STUCK ON PRESSURE STATUSES CAN FAIL THOUSANDS OF BATCHES IN A SINGLE PHASE.
    # THE CONSOLE GETS THE FIRST FEW FAILURES IN DETAIL AND A PERIODIC TALLY AFTER THAT --
    # NEVER ONE ERROR LINE PER FAILURE. THE COLLECTOR STILL RECEIVES EVERY FAILURE.
    server = RecordingServer(respond=fails_on(b"BOOM", httpx.ReadTimeout("simulated slow endpoint")))
    n_failing_batches = metadata_workflow._FailureDigest.DETAIL_LIMIT + 3
    guids = [f"BOOM-{i}" for i in range(n_failing_batches * EXPECTED_MAX_PER_REQUEST)]
    failures: list[metadata_workflow.FetchFailure] = []

    async def scenario() -> list:
        client = make_client(server)
        return await metadata_workflow.fetch(
            typed_guids={"LOGICAL_COLUMN": [guids]},
            failures=failures,
            http=client,
        )

    with caplog.at_level(logging.ERROR, logger="cs_tools.api.workflows.metadata"):
        asyncio.run(scenario())

    assert len(failures) == n_failing_batches

    # EVERY BATCH FAILED, BUT ONLY THE FIRST DETAIL_LIMIT GET THEIR OWN ERROR LINE. THE NEXT
    # TALLY WOULD ONLY APPEAR AT TALLY_EVERY FAILURES, SO NO OTHER ERROR RECORDS EXIST HERE.
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == metadata_workflow._FailureDigest.DETAIL_LIMIT
    assert all("Could not fetch data for" in r.getMessage() for r in errors)


def test_d_non_transport_errors_still_propagate():
    # TOLERATING A DROPPED REQUEST MUST NOT TURN A BUG INTO A SILENT PARTIAL EXTRACT.
    server = RecordingServer(respond=lambda _: RuntimeError("a bug, not a flaky network"))

    async def scenario() -> list:
        client = make_client(server)
        return await metadata_workflow.fetch(
            typed_guids={"LOGICAL_COLUMN": [["col-0"]]},
            http=client,
        )

    with pytest.raises(RuntimeError):
        asyncio.run(scenario())


# ANY VERSION ON THE security/metadata/fetch-permissions (V2) CODE PATH.
ANY_MODERN_TS_VERSION = awesomeversion.AwesomeVersion("10.5.0")


def test_e_a_failing_permission_request_does_not_abort_the_phase():
    # PERMISSIONS IS THE MOST SERVER-EXPENSIVE PHASE WE RUN, AND IT COMES LAST -- A SINGLE
    # FAILED REQUEST USED TO THROW AWAY EVERY PHASE THAT ALREADY SUCCEEDED BEFORE IT.
    server = RecordingServer(respond=fails_on(b"BOOM", httpx.ReadTimeout("simulated slow endpoint")))
    failures: list[metadata_workflow.FetchFailure] = []

    async def scenario() -> list:
        client = make_client(server)
        return await metadata_workflow.permissions(
            typed_guids={"LOGICAL_TABLE": ["good-1", "BOOM-1", "good-2"]},
            compat_ts_version=ANY_MODERN_TS_VERSION,
            failures=failures,
            http=client,
        )

    results = asyncio.run(scenario())

    # ONE PAYLOAD PER SURVIVING REQUEST -- THE SHAPE ITS TRANSFORMER EXPECTS.
    assert results == [[{"metadata_id": "OK"}], [{"metadata_id": "OK"}]]
    assert len(failures) == 1
    assert failures[0].metadata_type == "LOGICAL_TABLE"
    assert list(failures[0].identifiers) == ["BOOM-1"]
    assert isinstance(failures[0].error, httpx.HTTPError)


def test_e_a_failing_column_permission_request_reports_the_whole_column_batch():
    # COLUMN-ACCESS CALLERS PASS GROUPED LISTS (ONE PER TABLE); THE FAILURE RECORD MUST NAME
    # EVERY COLUMN THE LOST REQUEST COVERED.
    server = RecordingServer(respond=fails_on(b"BOOM", httpx.ReadError("simulated dropped response")))
    good = ["good-1", "good-2"]
    bad = ["BOOM-1", "BOOM-2"]
    failures: list[metadata_workflow.FetchFailure] = []

    async def scenario() -> list:
        client = make_client(server)
        return await metadata_workflow.permissions(
            typed_guids={"LOGICAL_COLUMN": [good, bad]},
            compat_ts_version=ANY_MODERN_TS_VERSION,
            failures=failures,
            http=client,
        )

    results = asyncio.run(scenario())

    assert results == [[{"metadata_id": "OK"}]]
    assert len(failures) == 1
    assert list(failures[0].identifiers) == bad


def test_e_a_healthy_permissions_run_reports_no_failures():
    server = RecordingServer(respond=lambda _: 200)
    failures: list[metadata_workflow.FetchFailure] = []

    async def scenario() -> list:
        client = make_client(server)
        return await metadata_workflow.permissions(
            typed_guids={"LOGICAL_TABLE": ["tbl-1", "tbl-2"]},
            compat_ts_version=ANY_MODERN_TS_VERSION,
            failures=failures,
            http=client,
        )

    results = asyncio.run(scenario())

    assert failures == []
    assert len(results) == 2


def test_f_dependent_fetch_failures_name_the_kind_of_fetch(caplog):
    # "25 LOGICAL_COLUMN objects" ALONE DOESN'T SAY WHAT WAS LOST -- THE SAME COLUMNS APPEAR
    # IN THE DETAILS, DEPENDENTS, AND COLUMN-ACCESS PHASES. THE MESSAGE MUST NAME THE KIND.
    server = RecordingServer(respond=fails_on(b"BOOM", httpx.ReadTimeout("simulated slow endpoint")))
    bad = [f"BOOM-{i}" for i in range(EXPECTED_MAX_PER_REQUEST)]
    failures: list[metadata_workflow.FetchFailure] = []

    async def scenario() -> None:
        client = make_client(server)
        await metadata_workflow.fetch(
            typed_guids={"LOGICAL_COLUMN": [bad]},
            include_dependent_objects=True,
            dependent_objects_record_size=-1,
            failures=failures,
            http=client,
        )

    with caplog.at_level(logging.ERROR, logger="cs_tools.api.workflows.metadata"):
        asyncio.run(scenario())

    assert "Could not fetch dependents for" in caplog.text
    assert failures[0].fetched == "dependents"


def test_f_permission_fetch_failures_name_the_kind_of_fetch(caplog):
    server = RecordingServer(respond=fails_on(b"BOOM", httpx.ReadTimeout("simulated slow endpoint")))
    failures: list[metadata_workflow.FetchFailure] = []

    async def scenario() -> None:
        client = make_client(server)
        await metadata_workflow.permissions(
            typed_guids={"LOGICAL_TABLE": ["BOOM-1"]},
            compat_ts_version=ANY_MODERN_TS_VERSION,
            failures=failures,
            http=client,
        )

    with caplog.at_level(logging.ERROR, logger="cs_tools.api.workflows.metadata"):
        asyncio.run(scenario())

    assert "Could not fetch permissions for" in caplog.text
    assert failures[0].fetched == "permissions"


def test_f_a_plain_fetch_still_says_data(caplog):
    # CALLERS WHICH SET NEITHER FLAG GET THE GENERIC WORDING.
    server = RecordingServer(respond=fails_on(b"BOOM", httpx.ReadTimeout("simulated slow endpoint")))
    failures: list[metadata_workflow.FetchFailure] = []

    async def scenario() -> None:
        client = make_client(server)
        await metadata_workflow.fetch(typed_guids={"LOGICAL_TABLE": ["BOOM-1"]}, failures=failures, http=client)

    with caplog.at_level(logging.ERROR, logger="cs_tools.api.workflows.metadata"):
        asyncio.run(scenario())

    assert "Could not fetch data for" in caplog.text
    assert failures[0].fetched == "data"


def test_f_an_error_with_no_message_has_no_dangling_colon(caplog):
    # ReadTimeout OFTEN CARRIES NO TEXT -- "(ReadTimeout: )" READS AS A BROKEN MESSAGE.
    server = RecordingServer(respond=fails_on(b"BOOM", httpx.ReadTimeout("")))

    async def scenario() -> None:
        client = make_client(server)
        await metadata_workflow.fetch(typed_guids={"LOGICAL_TABLE": ["BOOM-1"]}, http=client)

    with caplog.at_level(logging.ERROR, logger="cs_tools.api.workflows.metadata"):
        asyncio.run(scenario())

    assert "(ReadTimeout)" in caplog.text
    assert "ReadTimeout: " not in caplog.text
