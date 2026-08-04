from __future__ import annotations

from collections.abc import Coroutine, Iterable, Sequence
from typing import Any, Literal, NamedTuple, Optional, cast
import asyncio
import datetime as dt
import itertools as it
import json
import logging
import pathlib

from thoughtspot_tml.types import TMLObject
import awesomeversion
import httpx
import tenacity

from cs_tools import _types, utils
from cs_tools.api.client import RESTAPIClient
from cs_tools.api.workflows.utils import paginator

_LOG = logging.getLogger(__name__)

# THE MOST IDENTIFIERS WE PLACE IN A SINGLE metadata/search REQUEST. BOUNDING THIS KEEPS ONE
# WIDE OBJECT (eg. A TABLE WITH HUNDREDS OF COLUMNS) FROM BECOMING A SINGLE, ENORMOUS REQUEST,
# AND MANY SINGLE OBJECTS FROM BECOMING MANY REQUESTS. MIRRORS THE n=25 PRECEDENT IN
# RESTAPIClient.v1_security_metadata_permissions.
_MAX_IDENTIFIERS_PER_SEARCH = 25


async def fetch_all(
    metadata_types: Iterable[_types.APIObjectType],
    *,
    http: RESTAPIClient,
    record_size: int = 5_000,
    pattern: Optional[str] = None,
    **search_options,
) -> list[_types.APIResult]:
    """Wraps metadata/search fetching all objects of the given type and exhausts the pagination."""
    results: list[_types.APIResult] = []
    tasks: list[asyncio.Task] = []

    async with utils.BoundedTaskGroup(max_concurrent=len(list(metadata_types))) as g:
        for object_type in metadata_types:
            search_options["guid"] = ""
            search_options["metadata"] = [{"type": object_type, "name_pattern": pattern}]
            coro = paginator(http.metadata_search, record_size=record_size, **search_options)
            task = g.create_task(coro, name=object_type)
            tasks.append(task)

    for task in tasks:
        try:
            d = task.result()

        except httpx.HTTPError as e:
            _LOG.error(f"Could not fetch all objects for '{task.get_name()}' object type, see logs for details..")
            _LOG.debug(f"Full error: {e}", exc_info=True)
            continue

        results.extend(d)

    return results


def _flatten_identifiers(guids: Iterable[Any]) -> list[_types.GUID]:
    """Flatten a caller's identifiers (loose single guids and/or grouped lists) into one flat list."""
    flat: list[_types.GUID] = []

    for guid in guids:
        if isinstance(guid, str):
            flat.append(guid)
        else:
            flat.extend(guid)

    return flat


class FetchFailure(NamedTuple):
    """One batched API request which could not be fetched."""

    metadata_type: str
    identifiers: tuple[_types.GUID, ...]
    error: BaseException


class _FailureDigest:
    """
    Report request failures on the console as they happen.

    A failure storm (eg. a server stuck returning 502s) can fail thousands of requests in a single
    phase. One ERROR line per failure at that scale buries the phase warning and the end-of-run
    summary, so the console gets the first few failures in detail and a periodic tally after that.
    The logfile always receives every failure in full.
    """

    DETAIL_LIMIT = 5
    TALLY_EVERY = 250

    def __init__(self) -> None:
        self.n_failed = 0

    def record(self, metadata_type: str, identifiers: tuple[_types.GUID, ...], error: httpx.HTTPError) -> None:
        self.n_failed += 1

        if self.n_failed <= self.DETAIL_LIMIT:
            _LOG.error(
                f"Could not fetch data for {len(identifiers)} {metadata_type} objects "
                f"({type(error).__name__}: {error}), the extract will continue without them.."
            )
        elif self.n_failed % self.TALLY_EVERY == 0:
            _LOG.error(f"{self.n_failed:,} API requests have failed so far, the extract will continue..")

        _LOG.debug(f"Full error: {error}", exc_info=True)


async def _observed_request(
    coro: Coroutine,
    metadata_type: str,
    identifiers: tuple[_types.GUID, ...],
    digest: _FailureDigest,
) -> httpx.Response:
    """Await one batched request, reporting a failure the moment it happens."""
    try:
        try:
            r = await coro
        except tenacity.RetryError as error:
            # A SERVER STUCK ON PRESSURE STATUSES (429/502/503/504) EXHAUSTS THE RESULT-BASED RETRY
            # POLICY, WHICH SURFACES AS tenacity.RetryError WRAPPING THE LAST RESPONSE (reraise=True
            # ONLY COVERS EXCEPTION-BASED EXHAUSTION). UNWRAP IT SO IT FLOWS THROUGH THE SAME
            # STATUS-FAILURE PATH AS ANY OTHER ERROR RESPONSE.
            if error.last_attempt.failed:
                raise
            r = error.last_attempt.result()

        r.raise_for_status()

    except httpx.HTTPError as e:
        digest.record(metadata_type, identifiers, e)
        raise

    return r


def _sift_gathered_outcomes(
    batches: list[tuple[str, tuple[_types.GUID, ...]]],
    outcomes: Sequence[Any],
    *,
    failures: Optional[list[FetchFailure]] = None,
) -> list[Any]:
    """
    Split gathered request outcomes into their parsed payloads, reporting the failed batches.

    Failures were already reported on the console as they happened (see `_observed_request`). Here
    they are tallied into the phase warning, and reported to `failures` when the caller passes a
    collector, so it can report the gaps and decide whether an incomplete result is acceptable.
    """
    payloads: list[Any] = []
    missing_by_type: dict[str, int] = {}
    n_failed = 0

    for (metadata_type, identifiers), outcome in zip(batches, outcomes):
        # ONLY TRANSPORT AND STATUS FAILURES ARE TOLERATED. ANYTHING ELSE IS A BUG IN OUR OWN CODE
        # AND MUST STAY LOUD, RATHER THAN BECOMING A SILENTLY INCOMPLETE EXTRACT.
        if isinstance(outcome, httpx.HTTPError):
            missing_by_type[metadata_type] = missing_by_type.get(metadata_type, 0) + len(identifiers)
            n_failed += 1

            if failures is not None:
                failures.append(FetchFailure(metadata_type=metadata_type, identifiers=identifiers, error=outcome))

            continue

        if isinstance(outcome, BaseException):
            raise outcome

        payloads.append(outcome.json())

    if n_failed:
        *rest, last = [f"{count:,} {metadata_type}" for metadata_type, count in missing_by_type.items()]
        missing = f"{', '.join(rest)} and {last}" if rest else last

        # ONLY THE CALLERS WHICH COLLECT FAILURES REPORT AN END-OF-RUN SUMMARY.
        followup = " A summary follows at the end of the run." if failures is not None else ""

        _LOG.warning(
            f"{n_failed:,} of {len(batches):,} API requests failed after retries. The extract will "
            f"continue, but data for up to {missing} objects will be missing from this run. Each "
            f"failure is recorded in the logfile.{followup}"
        )

    return payloads


async def fetch(
    typed_guids: dict[_types.APIObjectType, Iterable[_types.GUID]],
    *,
    http: RESTAPIClient,
    record_size: int = 5_000,
    failures: Optional[list[FetchFailure]] = None,
    **search_options,
) -> list[_types.APIResult]:
    """
    Wraps metadata/search fetching specific objects.

    A batch which cannot be fetched -- after the client's own retries are exhausted -- is skipped
    instead of cancelling its siblings. Dependent lists are unbounded and cannot be paginated, so a
    request can always exceed the read timeout; one dropped batch must not cost the entire extract.

    Skipped batches are always logged, and are reported to `failures` when the caller passes a
    collector, so it can report the gaps and decide whether an incomplete result is acceptable.
    """
    # WHY 10? metadata/search IS THE HEAVIEST READ WE MAKE, AND THE TRANSPORT'S OWN LIMIT IS SHARED
    # WITH EVERY OTHER CALLER. HOLD BACK A FEW SLOTS SO ONE PHASE CAN'T MONOPOLISE THE CLIENT.
    CONCURRENCY_MAGIC_NUMBER = 10

    batches: list[tuple[_types.APIObjectType, tuple[_types.GUID, ...]]] = []
    coros: list[Coroutine] = []
    digest = _FailureDigest()

    for metadata_type, guids in typed_guids.items():
        # CALLERS GROUP IDENTIFIERS INCONSISTENTLY (single guids, or per-object lists). FLATTEN
        # THEM, THEN RE-BATCH TO A BOUNDED SIZE SO REQUEST COST STAYS PREDICTABLE REGARDLESS OF
        # HOW WIDE OR NUMEROUS THE OBJECTS ARE.
        for batch in utils.batched(_flatten_identifiers(guids), n=_MAX_IDENTIFIERS_PER_SEARCH):
            identifiers = tuple(batch)
            options = {**search_options, "metadata": [{"type": metadata_type, "identifier": _} for _ in identifiers]}
            c = http.metadata_search(guid="", record_size=record_size, **options)
            coros.append(_observed_request(c, metadata_type, identifiers, digest))
            batches.append((metadata_type, identifiers))

    # return_exceptions=True IS THE WHOLE POINT: a TaskGroup WOULD CANCEL EVERY SIBLING ON THE
    # FIRST FAILURE, WHICH IS WHAT USED TO THROW AWAY ~25 MINUTES OF COMPLETED WORK.
    outcomes = await utils.bounded_gather(*coros, max_concurrent=CONCURRENCY_MAGIC_NUMBER, return_exceptions=True)

    results: list[_types.APIResult] = []

    for payload in _sift_gathered_outcomes(batches, outcomes, failures=failures):
        results.extend(payload)

    return results


async def fetch_one(
    identifier: _types.ObjectIdentifier | _types.PrincipalIdentifier | _types.OrgIdentifier,
    metadata_type: _types.APIObjectType | Literal["ORG"],
    *,
    attr_path: str | None = None,
    http: RESTAPIClient,
    **search_options,
) -> _types.APIResult | Any:
    """
    Wraps */search APIs to fetch a single object and optionally return its attribute.

    attr_path is a jq-like path to try on the returned object from the API, separated by double-underscores.

    Example:
       attr_path = 'metadata_header__id'

       d = r.json()
       d["metadata_header"]["id"]
    """
    if metadata_type == "ORG":
        r = await http.orgs_search(org_identifier=identifier, **search_options)
    else:
        search_options["metadata"] = [{"type": metadata_type, "identifier": identifier}]
        r = await http.metadata_search(guid="", **search_options)

    try:
        r.raise_for_status()
        _ = next(iter(r.json()))
    except httpx.HTTPError as e:
        _LOG.debug(f"Full error: {e}", exc_info=True)
        raise ValueError(f"Could not find the {metadata_type} for the given identifier {identifier}") from None
    except StopIteration:
        raise ValueError(f"Could not find the {metadata_type} for the given identifier {identifier}") from None

    if attr_path is None:
        return _

    nested = _

    # SEARCH OBJECTS DEEPLY NESTED.
    for path in attr_path.split("__"):
        try:
            nested = nested[int(path) if path.isdigit() else path]
        except (KeyError, IndexError) as e:
            _LOG.debug(f"Full object: {json.dumps(_, indent=4)}\n")
            _LOG.debug(f" Sub object: {json.dumps(_, indent=4)}\n")
            _LOG.debug(f"Error: {e}", exc_info=True)
            raise ValueError(f"Could not fetch sub-object at path '{path}', see logs for details..") from None

    return nested


async def tag_all(guids: Iterable[_types.GUID], *, tags: Iterable[str], http: RESTAPIClient, **tag_options) -> None:
    """Tag all objects."""
    CONCURRENCY_MAGIC_NUMBER = 15  # Why? It matches HTTP request concurrency.

    async with utils.BoundedTaskGroup(max_concurrent=CONCURRENCY_MAGIC_NUMBER) as g:
        for tag_name in tags:
            coro = http.tags_create(name=tag_name, **tag_options)
            task = g.create_task(coro, name=tag_name)

    tasks: list[asyncio.Task] = []

    async with utils.BoundedTaskGroup(max_concurrent=CONCURRENCY_MAGIC_NUMBER) as g:
        for guid in guids:
            for tag_name in tags:
                coro = http.tags_assign(guid=guid, tag=tag_name)
                task = g.create_task(coro, name=f"{guid}__{tag_name}")
                tasks.append(task)

    for task in tasks:
        try:
            r = task.result()
            r.raise_for_status()

        except httpx.HTTPError as e:
            guid, tag_name = task.get_name().split("__")
            _LOG.error(f"Could not tag the object for guid={guid} with tag={tag_name}, see logs for details..")
            _LOG.debug(f"Full error: {e}", exc_info=True)
            continue

        # results.extend(d)

    # return results


async def permissions(
    typed_guids: dict[_types.APIObjectType, Iterable[_types.GUID]],
    *,
    compat_ts_version: awesomeversion.AwesomeVersion,
    record_size: int = -1,
    failures: Optional[list[FetchFailure]] = None,
    http: RESTAPIClient,
    **permission_options,
) -> list[_types.APIResult]:
    """
    Wraps security/metadata/fetch-permissions fetching specific objects.

    Permissions is the most server-expensive data we fetch, and it runs last -- a request which
    fails after the client's own retries is skipped instead of cancelling its siblings, so one bad
    request cannot throw away every phase which already succeeded before it. Skipped requests are
    always logged, and are reported to `failures` when the caller passes a collector.
    """
    FIFTEEN_MINUTES = 60 * 15

    if compat_ts_version < "10.3.0":
        CONCURRENCY_MAGIC_NUMBER = 1  # Why? Fetching permissions could potentially be very expensive for the server.
    else:
        CONCURRENCY_MAGIC_NUMBER = 5  # Why? Fetching permissions could potentially be very expensive for the server.

    batches: list[tuple[_types.APIObjectType, tuple[_types.GUID, ...]]] = []
    coros: list[Coroutine] = []
    digest = _FailureDigest()

    for metadata_type, guids in typed_guids.items():
        for guid in guids:
            # DEV NOTE: @boonhapus, 2024/11/25
            # 10.3.0 IS WHEN WE RELEASED .permission_type={DEFINED|EFFECTIVE} FOR THE
            # ENDPOINT security/metadata/fetch-permissions , PRIOR TO THIS, THE DEFAULT
            # WAS TO FETCH EFFECTIVE PERMISSIONS.
            #
            # ONCE 10.3.0.SW IS N-2, WE CAN SWITCH FROM typed_guids -> guids .
            #
            if compat_ts_version < "10.3.0":
                # A SINGLE OBJECT
                if isinstance(guid, str):
                    permission_options["id"] = [guid]

                # AN ARRAY OF OBJECTS
                if isinstance(guid, list):
                    permission_options["id"] = guid

                c = http.v1_security_metadata_permissions(guid="", api_object_type=metadata_type, **permission_options)
            # //
            else:
                permission_options["timeout"] = FIFTEEN_MINUTES

                # A SINGLE OBJECT
                if isinstance(guid, str):
                    permission_options["metadata"] = [{"type": metadata_type, "identifier": guid}]

                # AN ARRAY OF OBJECTS
                if isinstance(guid, list):
                    permission_options["metadata"] = [{"type": metadata_type, "identifier": _} for _ in guid]

                c = http.security_metadata_permissions(guid="", record_size=record_size, **permission_options)

            identifiers = (guid,) if isinstance(guid, str) else tuple(guid)
            coros.append(_observed_request(c, metadata_type, identifiers, digest))
            batches.append((metadata_type, identifiers))

    # return_exceptions=True: a TaskGroup WOULD CANCEL EVERY SIBLING ON THE FIRST FAILURE,
    # DESTROYING THE ENTIRE EXTRACT IN ITS FINAL PHASE.
    outcomes = await utils.bounded_gather(*coros, max_concurrent=CONCURRENCY_MAGIC_NUMBER, return_exceptions=True)

    # ONE PAYLOAD PER SURVIVING REQUEST -- THE SHAPE THE PERMISSIONS TRANSFORMER EXPECTS.
    return _sift_gathered_outcomes(batches, outcomes, failures=failures)


async def dependents(guid: _types.GUID, *, http: RESTAPIClient) -> list[_types.APIResult]:
    """Fetch all dependents of a given object, regardless of its type."""
    r = await http.metadata_search(
        guid=guid, include_details=True, include_dependent_objects=True, dependent_objects_record_size=-1
    )

    r.raise_for_status()
    _: _types.APIResult = next(iter(r.json()), {})

    # DEV NOTE: @boonhapus, 2024/11/30
    # metadata/search?include_dependent_objects=True DOESN'T WORK FOR CONNECTIONS.
    if _["metadata_type"] == "CONNECTION":
        track_top_level_info = True
        coros: list[Coroutine] = []

        for logical_table in _["metadata_detail"]["logicalTableList"]:
            guid = logical_table["header"]["id"]
            c = http.metadata_search(guid=guid, include_dependent_objects=True, dependent_objects_record_size=-1)
            coros.append(c)

        _ = await asyncio.gather(*coros)  # type: ignore[assignment]
        d = cast(Iterable[_types.APIResult], it.chain.from_iterable(r.json() for r in _))  # type: ignore[attr-defined]
    else:
        track_top_level_info = False
        d = cast(Iterable[_types.APIResult], [_])

    all_dependents: list[_types.APIResult] = []
    seen: set[_types.GUID] = set()

    for metadata_object in d:
        if track_top_level_info and metadata_object["metadata_id"] not in seen:
            all_dependents.append(
                {
                    "guid": metadata_object["metadata_id"],
                    "name": metadata_object["metadata_name"],
                    "type": _types.lookup_metadata_type(metadata_object["metadata_type"], mode="V1_TO_API"),
                    "author_guid": metadata_object["metadata_header"]["author"],
                    "author_name": metadata_object["metadata_header"]["authorName"],
                    "tags": metadata_object["metadata_header"]["tags"],
                    "last_modified": dt.datetime.fromtimestamp(
                        metadata_object["metadata_header"]["modified"] / 1000, tz=dt.timezone.utc
                    ),
                }
            )

            seen.add(metadata_object["metadata_id"])

        for dependent_info in metadata_object["dependent_objects"].values():
            for dependent_type, dependents in dependent_info.items():
                for dependent in dependents:
                    if dependent["id"] in seen:
                        continue

                    all_dependents.append(
                        {
                            "guid": dependent["id"],
                            "name": dependent["name"],
                            "type": _types.lookup_metadata_type(dependent_type, mode="V1_TO_API"),
                            "author_guid": dependent["author"],
                            "author_name": dependent.get("authorName", "UNKNOWN"),
                            "tags": dependent["tags"],
                            "last_modified": dt.datetime.fromtimestamp(
                                dependent["modified"] / 1000, tz=dt.timezone.utc
                            ),
                        }
                    )

                    seen.add(dependent["id"])

    return all_dependents


async def tml_export(
    guid: _types.GUID,
    *,
    directory: pathlib.Path | None = None,
    http: RESTAPIClient,
    **tml_export_options,
) -> _types.APIResult:
    """Export a metadata object, optionally to a directory."""
    try:
        r = await http.metadata_tml_export(guid=guid, **tml_export_options)
        r.raise_for_status()

        d = next(iter(r.json()))

        if d["info"]["status"]["status_code"] == "ERROR":
            raise ValueError(d["info"])

    except (httpx.HTTPStatusError, StopIteration):
        _LOG.error(f"Unable to export {guid}, see log for details..")
        _LOG.debug(r.text)
        return {"edoc": None, "info": {"id": guid, "status": {"status_code": "ERROR"}, "httpx_response": r.text}}

    except ValueError as e:
        _LOG.error(f"Unable to export {guid}, see log for details..")
        _LOG.debug(e.args[0])
        return {"edoc": None, "info": {"id": guid, **e.args[0]}}

    if directory is not None:
        i = d["info"]
        directory.joinpath(i["type"]).mkdir(parents=True, exist_ok=True)
        directory.joinpath(f"{i['type']}/{i['id']}.{i['type']}.tml").write_text(d["edoc"], encoding="utf-8")

    return d


async def tml_import(
    tmls: list[TMLObject],
    *,
    policy: _types.TMLImportPolicy = "ALL_OR_NONE",
    use_async_endpoint: bool = False,
    wait_for_completion: bool = False,
    log_errors: bool = False,
    http: RESTAPIClient,
    **tml_import_options,
) -> _types.APIResult:
    """Import a metadata object, alerting about warnings and errors."""
    if use_async_endpoint:
        _LOG.debug(f"Async import initiated on {len(tmls):,} objects (behave synchronously: {wait_for_completion}).")
        r = await http.metadata_tml_async_import(tmls=[t.dumps() for t in tmls], policy=policy, **tml_import_options)
        r.raise_for_status()
        d = r.json()

        _LOG.debug(f"RAW DATA\n{json.dumps(d, indent=2, default=str)}\n")

        # IF WE'RE NOT WAITING FOR THE JOB TO COMPLETE, RETURN THE ASYNC JOB INFO DIRECTLY.
        if not wait_for_completion:
            return d

        async_job_id = d["task_id"]

        # AFTER FIVE 5-second ITERATIONS (25s), WE'LL ELEVATE THE LOGGING LEVEL.
        n_iterations = 0

        # OTHERWISE, PROCESS THE JOB AS IF IT WERE A SYNCHRONOUS PAYLOAD.
        while d.get("task_status") != "COMPLETED":
            log_level = logging.DEBUG if n_iterations < 5 else logging.INFO
            n_iterations += 1
            _LOG.log(log_level, f"Checking status of asynchronous import {async_job_id}")
            _ = await asyncio.sleep(5)  # type: ignore[func-returns-value]
            r = await http.metadata_tml_async_status(task_ids=[async_job_id])
            r.raise_for_status()

            # RAW DATA
            _ = r.json()
            _LOG.debug(f"RAW DATA\n{json.dumps(_, indent=2, default=str)}\n")

            # FIRST STATUS (we only 1 in job), BUT ONLY REASSIGN while LOOP VAR IF THE KEY EXISTS.
            d = next(iter(_["status_list"]), d)
            _LOG.log(log_level, f"TASK ID: {async_job_id}\n{json.dumps(d, indent=2, default=str)}\n")

        # POST-PROCESSING TO MIMIC THE SYNCHRONOUS RESPONSE.
        d = d["import_response"]["object"]

    else:
        r = await http.metadata_tml_import(tmls=[t.dumps() for t in tmls], policy=policy, **tml_import_options)
        r.raise_for_status()
        d = r.json()

    if log_errors:
        for tml_import_info, tml in zip(d, tmls):
            tml_type = tml.tml_type_name.upper()

            if tml_import_info["response"]["status"]["status_code"] == "ERROR":
                errors = tml_import_info["response"]["status"]["error_message"].replace("<br/>", "\n")
                _LOG.error(f"{tml_type} '{tml.name}' failed to import, ThoughtSpot errors:\n[fg-error]{errors}")

            if tml_import_info["response"]["status"]["status_code"] == "WARNING":
                errors = tml_import_info["response"]["status"]["error_message"].replace("<br/>", "\n")
                _LOG.warning(f"{tml_type} '{tml.name}' partially imported, ThoughtSpot errors:\n[fg-warn]{errors}")

            if tml_import_info["response"]["status"]["status_code"] == "OK":
                _LOG.debug(f"{tml_type} '{tml.name}' successfully imported")

    return d
