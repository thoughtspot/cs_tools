"""
Spec for the searchable schedules extract (ts_schedule + ts_schedule_run).

Payload facts pinned from api/rest/2.0/schedules/search on a 26.8.0 cloud cluster:

  1. `creation_time_in_millis` and the run `*_time_in_millis` fields hold epoch SECONDS despite
     the name. A row must land in 2024, not 1970. If the API is ever corrected to real millis the
     same coercion must still land on the right day.
  2. `frequency.cron_expression` is a dict (second/minute/hour/day_of_month/month/day_of_week),
     not a string. It is stored as JSON text so no information is lost.
  3. `history_runs` is opt-in, a rolling ~30-day window, and absent (or empty) for schedules that
     never ran. A schedule with no runs still yields a schedule row and zero run rows.
  4. Schedules are a snapshot table: snapshot_date is part of the primary key so history
     accumulates under any load strategy. Runs are keyed by their own guid.
  5. The schedules/search wrapper sends no `metadata` filter when no liveboard is given, so the
     call is cluster-wide (org-scoped by the session). With a liveboard it filters to that one.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import inspect
import json
import logging

from cs_tools.api.client import RESTAPIClient
from cs_tools.cli.tools.searchable import api_transformer as T
from cs_tools.cli.tools.searchable.app import (
    SCHEDULE_PAGE_SIZE,
    _fetch_schedules,
    metadata as metadata_command,
)
from cs_tools.cli.tools.searchable.models import METADATA_MODELS, SCHEDULE_MODELS, Schedule, ScheduleRun
from cs_tools.sync.sqlite.syncer import SQLite
import httpx
import sqlalchemy as sa

CLUSTER = "cluster-1"
SNAPSHOT = dt.date(2026, 9, 17)


def _run(**overrides) -> dict:
    base = {
        "id": "run-1",
        "start_time_in_millis": 1_789_398_000,  # 2026-09-14, in SECONDS
        "end_time_in_millis": 1_789_398_060,
        "status": "FAILED",
        "detail": "Error Code: 12727\nError Message: Author does not have download permissions.",
    }
    base.update(overrides)
    return base


def _schedule(**overrides) -> dict:
    base = {
        "id": "sched-1",
        "name": "Weekly Marketing",
        "description": "",
        "status": "PAUSED",
        "author": {"id": "user-1", "name": "someone"},
        "creation_time_in_millis": 1_717_599_587,  # 2024-06-05, in SECONDS
        "file_format": "PDF",
        "time_zone": "America/Chicago",
        "frequency": {
            "cron_expression": {
                "second": "0",
                "minute": "00",
                "hour": "10",
                "day_of_month": "*",
                "month": "*",
                "day_of_week": "1",
            }
        },
        "metadata": {"id": "lb-1", "name": "Marketing Liveboard", "type": "LIVEBOARD"},
        "recipient_details": {"emails": ["a@example.com"], "principals": [{"identifier": "user-1", "type": "USER"}]},
        "history_runs": [_run(), _run(id="run-2", status="SUCCESS", detail="Scheduled updates generated as expected.")],
    }
    base.update(overrides)
    return base


# --- models are registered ---------------------------------------------------


def test_schedule_models_are_opt_in_not_part_of_the_default_extract():
    # THE SYNCER CREATES EVERY MODEL IN METADATA_MODELS ON CONNECT, BEFORE THE COMMAND BODY RUNS.
    # KEEPING THE SCHEDULE MODELS OUT OF IT IS WHAT KEEPS A DEFAULT `searchable metadata` RUN
    # FREE OF SCHEDULE WORK: NO EXTRA CALLS, NO EMPTY TABLES IN THE WAREHOUSE.
    assert Schedule not in METADATA_MODELS
    assert ScheduleRun not in METADATA_MODELS
    assert SCHEDULE_MODELS == [Schedule, ScheduleRun]


def test_include_schedules_flag_is_off_by_default():
    option = inspect.signature(metadata_command).parameters["include_schedules"].default
    assert option.default is False
    assert "--include-schedules" in option.param_decls


def test_database_syncer_can_register_the_schedule_tables_after_connect(tmp_path):
    # THE TARGET SYNCER IS BUILT (AND ITS TABLES CREATED) WHILE OPTIONS ARE PARSED, BEFORE WE KNOW
    # THE FLAG. WHEN THE FLAG IS ON, THE COMMAND REGISTERS THE TWO EXTRA TABLES AT THAT POINT.
    syncer = SQLite(database_path=tmp_path / "t.db", models=METADATA_MODELS, load_strategy="UPSERT")
    before = set(sa.inspect(syncer._engine).get_table_names())
    assert "ts_schedule" not in before

    syncer.ensure_tables(SCHEDULE_MODELS)
    syncer.ensure_tables(SCHEDULE_MODELS)  # idempotent

    after = set(sa.inspect(syncer._engine).get_table_names())
    assert {"ts_schedule", "ts_schedule_run"} <= after
    assert after - before == {"ts_schedule", "ts_schedule_run"}

    # AND DUMPING INTO THEM WORKS LIKE ANY OTHER TABLE
    syncer.dump("ts_schedule", data=T.ts_schedule([_schedule()], cluster=CLUSTER, org_id=0, snapshot_date=SNAPSHOT))
    syncer.dump("ts_schedule_run", data=T.ts_schedule_run([_schedule()], cluster=CLUSTER, org_id=0))


def test_schedule_is_snapshot_keyed_and_run_is_guid_keyed():
    assert {c.name for c in Schedule.__table__.primary_key} == {
        "cluster_guid",
        "org_id",
        "snapshot_date",
        "schedule_guid",
    }
    assert {c.name for c in ScheduleRun.__table__.primary_key} == {
        "cluster_guid",
        "org_id",
        "schedule_guid",
        "run_guid",
    }


# --- ts_schedule -------------------------------------------------------------


def test_schedule_row_shape():
    rows = T.ts_schedule([_schedule()], cluster=CLUSTER, org_id=0, snapshot_date=SNAPSHOT)

    assert len(rows) == 1
    row = rows[0]
    assert row["cluster_guid"] == CLUSTER
    assert row["org_id"] == 0
    assert row["snapshot_date"] == SNAPSHOT
    assert row["schedule_guid"] == "sched-1"
    assert row["name"] == "Weekly Marketing"
    assert row["description"] is None  # empty string is stored as NULL, like every other table
    assert row["status"] == "PAUSED"
    assert row["author_guid"] == "user-1"
    assert row["liveboard_guid"] == "lb-1"
    assert row["file_format"] == "PDF"
    assert row["time_zone"] == "America/Chicago"


def test_schedule_created_is_seconds_not_millis():
    rows = T.ts_schedule([_schedule()], cluster=CLUSTER, org_id=0, snapshot_date=SNAPSHOT)
    assert rows[0]["created"] == dt.datetime(2024, 6, 5, 14, 59, 47, tzinfo=dt.timezone.utc)


def test_schedule_created_tolerates_real_millis_if_the_api_is_ever_fixed():
    rows = T.ts_schedule(
        [_schedule(creation_time_in_millis=1_717_599_587_000)], cluster=CLUSTER, org_id=0, snapshot_date=SNAPSHOT
    )
    assert rows[0]["created"].date() == dt.date(2024, 6, 5)


def test_schedule_created_missing_is_null():
    payload = _schedule()
    del payload["creation_time_in_millis"]
    rows = T.ts_schedule([payload], cluster=CLUSTER, org_id=0, snapshot_date=SNAPSHOT)
    assert rows[0]["created"] is None


def test_schedule_cron_is_stored_as_json_text():
    rows = T.ts_schedule([_schedule()], cluster=CLUSTER, org_id=0, snapshot_date=SNAPSHOT)
    assert json.loads(rows[0]["cron_expression"]) == {
        "second": "0",
        "minute": "00",
        "hour": "10",
        "day_of_month": "*",
        "month": "*",
        "day_of_week": "1",
    }


def test_schedule_recipients_are_counted_and_kept():
    rows = T.ts_schedule([_schedule()], cluster=CLUSTER, org_id=0, snapshot_date=SNAPSHOT)
    assert rows[0]["recipient_email_count"] == 1
    assert rows[0]["recipient_principal_count"] == 1
    assert json.loads(rows[0]["recipients"]) == {
        "emails": ["a@example.com"],
        "principals": [{"identifier": "user-1", "type": "USER"}],
    }


def test_schedule_with_no_recipients_or_time_zone():
    payload = _schedule(recipient_details={"emails": [], "principals": []}, time_zone="")
    rows = T.ts_schedule([payload], cluster=CLUSTER, org_id=0, snapshot_date=SNAPSHOT)
    assert rows[0]["recipient_email_count"] == 0
    assert rows[0]["recipient_principal_count"] == 0
    assert rows[0]["time_zone"] is None


def test_schedule_snapshot_date_defaults_to_today_utc():
    rows = T.ts_schedule([_schedule()], cluster=CLUSTER, org_id=0)
    assert rows[0]["snapshot_date"] == dt.datetime.now(tz=dt.timezone.utc).date()


# --- ts_schedule_run ---------------------------------------------------------


def test_run_rows_one_per_history_run():
    rows = T.ts_schedule_run([_schedule()], cluster=CLUSTER, org_id=0)

    assert [r["run_guid"] for r in rows] == ["run-1", "run-2"]
    assert all(r["schedule_guid"] == "sched-1" for r in rows)
    assert rows[0]["status"] == "FAILED"
    assert rows[0]["detail"].startswith("Error Code: 12727")
    assert rows[1]["status"] == "SUCCESS"


def test_run_times_are_seconds_not_millis():
    rows = T.ts_schedule_run([_schedule()], cluster=CLUSTER, org_id=0)
    assert rows[0]["started"] == dt.datetime(2026, 9, 14, 15, 0, 0, tzinfo=dt.timezone.utc)
    assert rows[0]["ended"] == dt.datetime(2026, 9, 14, 15, 1, 0, tzinfo=dt.timezone.utc)


def test_schedule_without_history_yields_schedule_row_and_no_run_rows():
    never_ran = _schedule(id="sched-2", history_runs=[])
    omitted = _schedule(id="sched-3")
    del omitted["history_runs"]

    assert len(T.ts_schedule([never_ran, omitted], cluster=CLUSTER, org_id=0, snapshot_date=SNAPSHOT)) == 2
    assert T.ts_schedule_run([never_ran, omitted], cluster=CLUSTER, org_id=0) == []


def test_run_missing_end_time_is_null():
    payload = _schedule(history_runs=[_run(end_time_in_millis=None)])
    rows = T.ts_schedule_run([payload], cluster=CLUSTER, org_id=0)
    assert rows[0]["ended"] is None


def test_schedule_with_deleted_author_still_yields_a_row():
    # A SCHEDULE OUTLIVES ITS AUTHOR. THE EXTRACT MUST KEEP THE ROW WITH A NULL, NOT CRASH.
    payload = _schedule(author=None)
    rows = T.ts_schedule([payload], cluster=CLUSTER, org_id=0, snapshot_date=SNAPSHOT)
    assert rows[0]["author_guid"] is None


# --- fetch step: a cluster that cannot answer is a warning, not a failed extract -----


def _client_answering(handler) -> RESTAPIClient:
    return RESTAPIClient(base_url="https://customer.thoughtspot.cloud", wrapped_transport=httpx.MockTransport(handler))


def test_fetch_schedules_returns_rows_on_success():
    client = _client_answering(lambda _: httpx.Response(200, json=[_schedule()]))

    rows = _fetch_schedules(client, org_id=0)

    assert [r["id"] for r in rows] == ["sched-1"]


def _paged_server(pages: list[list[dict]], *, fail_on_offset: int | None = None):
    """Serve `pages` by record_offset, the way schedules/search does. Records every request body."""
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        if fail_on_offset is not None and body["record_offset"] == fail_on_offset:
            raise httpx.ReadTimeout("simulated slow page")
        index = body["record_offset"] // SCHEDULE_PAGE_SIZE
        return httpx.Response(200, json=pages[index] if index < len(pages) else [])

    return handler, seen


def test_fetch_schedules_walks_pages_instead_of_one_unbounded_request():
    # ONE UNBOUNDED REQUEST WITH FULL RUN HISTORY IS ~3KB PER SCHEDULE. A CLUSTER WITH THOUSANDS OF
    # SCHEDULES WOULD BE A SINGLE MULTI-MB RESPONSE AGAINST A FLAT TIMEOUT -- THE SAME SHAPE THAT
    # MAKES THE DEPENDENTS FETCH TIME OUT. PAGE IT.
    full_page = [_schedule(id=f"sched-{i}") for i in range(SCHEDULE_PAGE_SIZE)]
    last_page = [_schedule(id="sched-last")]
    handler, seen = _paged_server([full_page, last_page])

    rows = _fetch_schedules(_client_answering(handler), org_id=0)

    assert len(rows) == SCHEDULE_PAGE_SIZE + 1
    assert rows[-1]["id"] == "sched-last"
    assert [b["record_offset"] for b in seen] == [0, SCHEDULE_PAGE_SIZE]
    assert all(b["record_size"] == SCHEDULE_PAGE_SIZE for b in seen)
    assert all(b["history_runs_options"]["include_history_runs"] for b in seen)


def test_fetch_schedules_short_first_page_makes_exactly_one_request():
    handler, seen = _paged_server([[_schedule()]])

    rows = _fetch_schedules(_client_answering(handler), org_id=0)

    assert [r["id"] for r in rows] == ["sched-1"]
    assert len(seen) == 1


def test_fetch_schedules_keeps_earlier_pages_when_a_later_page_fails(caplog):
    # PARTIAL AND LOUD: WHAT WAS FETCHED IS KEPT, THE GAP IS LOGGED.
    full_page = [_schedule(id=f"sched-{i}") for i in range(SCHEDULE_PAGE_SIZE)]
    handler, _ = _paged_server([full_page, [_schedule(id="never-seen")]], fail_on_offset=SCHEDULE_PAGE_SIZE)

    with caplog.at_level(logging.WARNING):
        rows = _fetch_schedules(_client_answering(handler), org_id=0)

    assert len(rows) == SCHEDULE_PAGE_SIZE
    assert "ReadTimeout" in caplog.text
    assert "record_offset 500" in caplog.text or "page 2" in caplog.text


def test_fetch_schedules_on_an_older_cluster_is_empty_with_a_warning(caplog):
    # RELEASES WITHOUT THE ENDPOINT ANSWER 404 (OR 400 FOR UNKNOWN OPTIONS). NOT A FAILED EXTRACT.
    client = _client_answering(lambda _: httpx.Response(404, json={"error": "not found"}))

    with caplog.at_level(logging.WARNING):
        rows = _fetch_schedules(client, org_id=7)

    assert rows == []
    assert "Could not fetch schedules in org 7" in caplog.text
    assert "404" in caplog.text


def test_fetch_schedules_on_a_timeout_is_empty_with_a_warning(caplog):
    def slow(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated slow endpoint")

    client = _client_answering(slow)

    with caplog.at_level(logging.WARNING):
        rows = _fetch_schedules(client, org_id=0)

    assert rows == []
    assert "ReadTimeout" in caplog.text


# --- client wrapper ----------------------------------------------------------


def _client_capturing(requests: list[httpx.Request]) -> RESTAPIClient:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[])

    return RESTAPIClient(base_url="https://customer.thoughtspot.cloud", wrapped_transport=httpx.MockTransport(handler))


def test_schedules_search_without_liveboard_sends_no_metadata_filter():
    seen: list[httpx.Request] = []
    client = _client_capturing(seen)

    asyncio.run(client.schedules_search(record_size=-1, record_offset=0))

    body = json.loads(seen[0].content)
    assert "metadata" not in body
    assert body["record_size"] == -1


def test_schedules_search_with_liveboard_still_filters():
    seen: list[httpx.Request] = []
    client = _client_capturing(seen)

    asyncio.run(client.schedules_search("lb-1"))

    body = json.loads(seen[0].content)
    assert body["metadata"] == [{"identifier": "lb-1"}]
