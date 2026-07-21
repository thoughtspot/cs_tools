"""
Behavioral spec for cs_tools.api.workflows.metadata.fetch.

Drives the real fetch() through a production RESTAPIClient wired to an
in-memory httpx.MockTransport (via CachedRetryTransport's wrapped_transport
seam). No network access occurs.

Pins two properties customers depend on:

  1. fetch bounds the number of identifiers per metadata/search request,
     re-batching however the caller happened to group them. This keeps a
     single wide table (hundreds of columns) from becoming one giant, slow
     request, and keeps thousands of single objects from becoming thousands
     of requests.

  2. A single failing batch does not cancel its siblings. fetch returns the
     results it could gather instead of aborting the whole phase.
"""

from __future__ import annotations

from typing import Callable, Union
import asyncio
import json
import math

from cs_tools.api.client import RESTAPIClient
from cs_tools.api.workflows import metadata as metadata_workflow
import httpx

ANY_CLUSTER = "https://customer.thoughtspot.cloud"

# THE MOST IDENTIFIERS fetch SHOULD PLACE IN A SINGLE metadata/search REQUEST.
# MIRRORS THE EXISTING PRECEDENT IN client.v1_security_metadata_permissions (n=25).
EXPECTED_MAX_PER_REQUEST = 25

# WHEN A SEARCH ALSO PULLS DEPENDENTS, EACH REQUEST CARRIES ONE OBJECT'S (UNBOUNDED,
# NON-PAGINABLE) DEPENDENT LIST, SO fetch BATCHES FAR MORE CONSERVATIVELY.
EXPECTED_MAX_PER_REQUEST_WITH_DEPENDENTS = 1


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


def test_a_dependent_search_is_batched_one_object_at_a_time():
    # include_dependent_objects PULLS EACH OBJECT'S UNBOUNDED, NON-PAGINABLE DEPENDENT LIST.
    # PACKING 25 SUCH OBJECTS INTO ONE REQUEST BALLOONS INTO A MULTI-MINUTE QUERY THE SERVER
    # DROPS (ReadError), SO A WIDE IDENTIFIER LIST MUST BE SPLIT ONE OBJECT PER REQUEST.
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
    assert all(len(b) <= EXPECTED_MAX_PER_REQUEST_WITH_DEPENDENTS for b in batches), batches
    assert len(batches) == math.ceil(len(guids) / EXPECTED_MAX_PER_REQUEST_WITH_DEPENDENTS)
    # EVERY IDENTIFIER SENT, EXACTLY ONCE, IN ORDER.
    assert [g for batch in batches for g in batch] == guids


def test_a_plain_search_without_dependents_still_batches_at_25():
    # THE CONSERVATIVE ONE-AT-A-TIME BATCHING APPLIES ONLY WHEN DEPENDENTS ARE REQUESTED.
    # A PLAIN SEARCH KEEPS THE EFFICIENT 25-PER-REQUEST BATCHING.
    server = RecordingServer(respond=lambda _: 200)
    guids = [f"col-{i}" for i in range(60)]

    async def scenario() -> None:
        client = make_client(server)
        await metadata_workflow.fetch(
            typed_guids={"LOGICAL_COLUMN": [guids]},
            include_details=True,
            http=client,
        )

    asyncio.run(scenario())

    batches = server.sent_identifiers()
    assert all(len(b) <= EXPECTED_MAX_PER_REQUEST for b in batches), batches
    assert len(batches) == math.ceil(len(guids) / EXPECTED_MAX_PER_REQUEST)
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


def test_c_a_failing_batch_is_skipped_and_the_phase_returns_partial_results():
    # DELIBERATE CONTRACT CHANGE (fix C): a request that fails at the network level (after the
    # client's transport retries are exhausted) no longer aborts the whole phase. The failing
    # batch is logged and skipped; fetch returns whatever it could gather, so one slow object
    # can't sink an entire extract.
    def respond(request: httpx.Request) -> Union[int, Exception]:
        if b"BOOM" in request.content:
            return httpx.ReadTimeout("simulated slow endpoint")
        return 200

    server = RecordingServer(respond=respond)
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

    # DOES NOT RAISE; THE GOOD BATCHES COME BACK, THE FAILING ONES ARE SKIPPED.
    results = asyncio.run(scenario())
    assert len(results) == len(good)
