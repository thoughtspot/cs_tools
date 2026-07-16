"""
Integration tests for the CS Tools HTTP transport stack.

These drive a real RESTAPIClient — production retry policy, predicates, and
concurrency semaphore — against an in-memory httpx.MockTransport injected via
CachedRetryTransport's `wrapped_transport` seam. No network access occurs.

Complements tests/test_api_retry.py: that file specifies the retry predicates
and backoff in isolation; this file proves the client actually applies them.
"""

from __future__ import annotations

from typing import Union
import asyncio

from cs_tools.api.client import RESTAPIClient
import httpx
import pytest
import tenacity

ANY_CLUSTER = "https://customer.thoughtspot.cloud"
RETRY_SAFE_ENDPOINT = "api/rest/2.0/metadata/search"


class ScriptedServer:
    """
    An in-memory server which answers requests from a script.

    Each script entry is either an HTTP status code to respond with, or an
    Exception to raise. The final entry repeats for any further requests.
    """

    def __init__(self, script: list[Union[int, Exception]]):
        self.script = script
        self.calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:  # noqa: ARG002
        entry = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1

        if isinstance(entry, Exception):
            raise entry

        return httpx.Response(status_code=entry, json=[])


def make_client(server: ScriptedServer) -> tuple[RESTAPIClient, list[float]]:
    """Build a production-configured client against the scripted server, with recorded (not slept) retry waits."""
    client = RESTAPIClient(base_url=ANY_CLUSTER, wrapped_transport=httpx.MockTransport(server))

    recorded_sleeps: list[float] = []

    async def record_instead_of_sleeping(seconds: float) -> None:
        recorded_sleeps.append(seconds)

    client._transport.retrier.sleep = record_instead_of_sleeping  # type: ignore[union-attr]
    return client, recorded_sleeps


def test_default_wrapped_transport_is_a_real_http_transport():
    # WITHOUT INJECTION, THE CLIENT TALKS TO THE NETWORK THROUGH httpx AS ALWAYS.
    client = RESTAPIClient(base_url=ANY_CLUSTER)
    assert isinstance(client._transport._wrapper, httpx.AsyncHTTPTransport)  # type: ignore[union-attr]


def test_successful_request_is_sent_exactly_once():
    server = ScriptedServer(script=[200])

    async def scenario() -> httpx.Response:
        client, _ = make_client(server)
        return await client.request("POST", RETRY_SAFE_ENDPOINT, json={})

    r = asyncio.run(scenario())

    assert r.status_code == 200
    assert server.calls == 1


def test_server_pressure_is_retried_until_success():
    # A BUSY SERVER ANSWERS 502 TWICE, THEN RECOVERS. THE CALLER SEES ONLY THE
    # FINAL, HEALTHY RESPONSE.
    server = ScriptedServer(script=[502, 502, 200])

    async def scenario() -> httpx.Response:
        client, sleeps = make_client(server)
        r = await client.request("POST", RETRY_SAFE_ENDPOINT, json={})
        assert len(sleeps) == 2, "expected the policy to wait between each attempt"
        return r

    r = asyncio.run(scenario())

    assert r.status_code == 200
    assert server.calls == 3


def test_retry_exhaustion_stops_after_three_attempts():
    # A PERSISTENTLY UNHEALTHY SERVER: THE POLICY MUST GIVE UP, NOT LOOP FOREVER.
    # THE EXCEPTION SURFACE MAY EVOLVE, SO PIN THE ATTEMPT COUNT, NOT THE TYPE.
    server = ScriptedServer(script=[502])

    async def scenario() -> httpx.Response:
        client, _ = make_client(server)
        return await client.request("POST", RETRY_SAFE_ENDPOINT, json={})

    with pytest.raises((tenacity.RetryError, httpx.HTTPError)):
        asyncio.run(scenario())

    assert server.calls == 3


def test_transient_network_error_is_retried_until_success():
    # TRANSIENT NETWORK BLIPS ON A RETRY-SAFE ENDPOINT ARE RETRIED THROUGH,
    # RETURNING THE HEALTHY RESPONSE INSTEAD OF DYING ON THE FIRST BLIP.
    server = ScriptedServer(script=[httpx.ReadTimeout("blip"), httpx.ReadTimeout("blip"), 200])

    async def scenario() -> httpx.Response:
        client, _ = make_client(server)
        return await client.request("POST", RETRY_SAFE_ENDPOINT, json={})

    r = asyncio.run(scenario())

    assert r.status_code == 200
    assert server.calls == 3


def test_tml_import_is_never_resent_on_ambiguous_network_errors():
    # THE CLIENT METHOD MARKS ITS REQUEST NON-IDEMPOTENT, SO A ReadTimeout MUST
    # SURFACE ON THE FIRST ATTEMPT — THE IMPORT MAY HAVE BEEN APPLIED
    # SERVER-SIDE ALREADY, AND RE-SENDING IT COULD DUPLICATE CUSTOMER CONTENT.
    server = ScriptedServer(script=[httpx.ReadTimeout("blip"), 200])

    async def scenario() -> httpx.Response:
        client, _ = make_client(server)
        return await client.metadata_tml_import(tmls=["guid: fake"], policy="ALL_OR_NONE")

    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(scenario())

    assert server.calls == 1


def test_tml_import_is_never_resent_under_server_pressure():
    # SAME HAZARD, STATUS-CODE PATH: A 502 MEANS A GATEWAY GAVE UP, NOT THAT THE
    # SERVER STOPPED WORKING ON THE IMPORT. THE CALLER GETS THE 502 TO HANDLE.
    server = ScriptedServer(script=[502, 200])

    async def scenario() -> httpx.Response:
        client, _ = make_client(server)
        return await client.metadata_tml_import(tmls=["guid: fake"], policy="ALL_OR_NONE")

    r = asyncio.run(scenario())

    assert r.status_code == 502
    assert server.calls == 1
