from __future__ import annotations

from collections.abc import Coroutine, Iterable
from typing import Any, Literal, cast
import asyncio
import datetime as dt
import itertools as it
import json
import logging
import pathlib

from thoughtspot_tml.types import TMLObject
import awesomeversion
import httpx

from cs_tools import types, utils
from cs_tools.api.client import RESTAPIClient
from cs_tools.api.workflows.utils import paginator

log = logging.getLogger(__name__)


async def fetch_all(
    metadata_types: Iterable[types.APIObjectType],
    *,
    http: RESTAPIClient,
    record_size: int = 5_000,
    **search_options,
) -> list[types.APIResult]:
    """Wraps metadata/search fetching all objects of the given type and exhausts the pagination."""
    results: list[types.APIResult] = []
    tasks: list[asyncio.Task] = []

    async with utils.BoundedTaskGroup(max_concurrent=len(list(metadata_types))) as g:
        for object_type in metadata_types:
            search_options["guid"] = ""
            search_options["metadata"] = [{"type": object_type}]
            coro = paginator(http.metadata_search, record_size=record_size, **search_options)
            task = g.create_task(coro, name=object_type)
            tasks.append(task)

    for task in tasks:
        try:
            d = task.result()

        except httpx.HTTPError as e:
            log.error(f"Could not fetch all objects for '{task.get_name()}' object type, see logs for details..")
            log.debug(f"Full error: {e}", exc_info=True)
            continue

        results.extend(d)

    return results


async def fetch(
    typed_guids: dict[types.APIObjectType, Iterable[types.GUID]],
    *,
    http: RESTAPIClient,
    record_size: int = 5_000,
    **search_options,
) -> list[types.APIResult]:
    """Wraps metadata/search fetching specific objects and exhausts the pagination."""
    CONCURRENCY_MAGIC_NUMBER = 15  # Why? In case **search_options contains

    results: list[types.APIResult] = []
    tasks: list[asyncio.Task] = []

    async with utils.BoundedTaskGroup(max_concurrent=CONCURRENCY_MAGIC_NUMBER) as g:
        for metadata_type, guids in typed_guids.items():
            for guid in guids:
                # A SINGLE OBJECT
                if isinstance(guid, str):
                    search_options["metadata"] = [{"type": metadata_type, "identifier": guid}]

                # AN ARRAY OF OBJECTS
                if isinstance(guid, list):
                    search_options["metadata"] = [{"type": metadata_type, "identifier": _} for _ in guid]

                coro = http.metadata_search(guid="", record_size=record_size, **search_options)
                task = g.create_task(coro, name=guid)
                tasks.append(task)

    for task in tasks:
        try:
            r = task.result()
            r.raise_for_status()
            d = r.json()

        except httpx.HTTPError as e:
            log.error(f"Could not fetch the object for guid={task.get_name()}, see logs for details..")
            log.debug(f"Full error: {e}", exc_info=True)
            continue

        results.extend(d)

    return results


async def fetch_one(
    identifier: types.ObjectIdentifier | types.PrincipalIdentifier | types.OrgIdentifier,
    metadata_type: types.APIObjectType | Literal["ORG"],
    *,
    attr_path: str | None = None,
    http: RESTAPIClient,
    **search_options,
) -> types.APIResult | Any:
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
        log.debug(f"Full error: {e}", exc_info=True)
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
            log.debug(f"Full object: {json.dumps(_, indent=4)}\n")
            log.debug(f" Sub object: {json.dumps(_, indent=4)}\n")
            log.debug(f"Error: {e}", exc_info=True)
            raise ValueError(f"Could not fetch sub-object at path '{path}', see logs for details..") from None

    return nested


async def permissions(
    typed_guids: dict[types.APIObjectType, Iterable[types.GUID]],
    *,
    compat_ts_version: awesomeversion.AwesomeVersion,
    record_size: int = -1,
    http: RESTAPIClient,
    **permission_options,
) -> list[types.APIResult]:
    """Wraps security/metadata/fetch-permissions fetching specific objects and exhausts the pagination."""
    FIFTEEN_MINUTES = 60 * 15

    if compat_ts_version < "10.3.0":
        CONCURRENCY_MAGIC_NUMBER = 1  # Why? Fetching permissions could potentially be very expensive for the server.
    else:
        CONCURRENCY_MAGIC_NUMBER = 5  # Why? Fetching permissions could potentially be very expensive for the server.

    results: list[types.APIResult] = []
    tasks: list[asyncio.Task] = []

    async with utils.BoundedTaskGroup(max_concurrent=CONCURRENCY_MAGIC_NUMBER) as g:
        for metadata_type, guids in typed_guids.items():
            for _, guid in enumerate(guids):
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

                t = g.create_task(c, name=guid)
                tasks.append(t)

    for task in tasks:
        try:
            r = task.result()
            r.raise_for_status()
            d = r.json()

        except httpx.HTTPError as e:
            log.error(f"Could not fetch the permissions for guid={task.get_name()}, see logs for details..")
            log.debug(f"Full error: {e}", exc_info=True)
            continue

        results.append(d)

    return results


async def dependents(guid: types.GUID, *, http: RESTAPIClient) -> list[types.APIResult]:
    """Fetch all dependents of a given object, regardless of its type."""
    r = await http.metadata_search(
        guid=guid, include_details=True, include_dependent_objects=True, dependent_objects_record_size=-1
    )

    r.raise_for_status()
    _: types.APIResult = next(iter(r.json()), {})

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
        d = cast(Iterable[types.APIResult], it.chain.from_iterable(r.json() for r in _))  # type: ignore[attr-defined]
    else:
        track_top_level_info = False
        d = cast(Iterable[types.APIResult], [_])

    all_dependents: list[types.APIResult] = []
    seen: set[types.GUID] = set()

    for metadata_object in d:
        if track_top_level_info and metadata_object["metadata_id"] not in seen:
            all_dependents.append(
                {
                    "guid": metadata_object["metadata_id"],
                    "name": metadata_object["metadata_name"],
                    "type": types.lookup_api_type(metadata_object["metadata_type"]),
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
                            "type": types.lookup_api_type(dependent_type),
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
    guid: types.GUID,
    *,
    directory: pathlib.Path | None = None,
    http: RESTAPIClient,
    **tml_export_options,
) -> types.APIResult:
    """Export a metadata object, optionally to a directory."""
    try:
        r = await http.metadata_tml_export(guid=guid, **tml_export_options)
        r.raise_for_status()

        d = next(iter(r.json()))

        if d["info"]["status"]["status_code"] == "ERROR":
            raise ValueError(d["info"])

    except (httpx.HTTPStatusError, StopIteration):
        log.error(f"Unable to export {guid}, see log for details..")
        log.debug(r.text)
        return {"edoc": None, "info": {"id": guid}, "httpx_response": r.text}

    except ValueError as e:
        log.error(f"Unable to export {guid}, see log for details..")
        log.debug(e.args[0])
        return {"edoc": None, "info": e.args[0]}

    if directory is not None:
        i = d["info"]
        directory.joinpath(i["type"]).mkdir(parents=True, exist_ok=True)
        directory.joinpath(f"{i['type']}/{i['id']}.{i['type']}.tml").write_text(d["edoc"], encoding="utf-8")

    return d


async def tml_import(
    tmls: list[TMLObject],
    *,
    policy: types.ImportPolicy = "ALL_OR_NONE",
    http: RESTAPIClient,
    **tml_import_options,
) -> types.APIResult:
    """Import a metadata object, alerting about warnings and errors."""
    r = await http.metadata_tml_import(tmls=[t.dumps() for t in tmls], policy=policy, **tml_import_options)
    r.raise_for_status()

    for tml_import_info in r.json():
        idx = tml_import_info["request_index"]
        tml = tmls[idx]
        tml_type = tml.tml_type_name.upper()

        if tml_import_info["response"]["status"]["status_code"] == "ERROR":
            errors = tml_import_info["response"]["status"]["error_message"].replace("<br/>", "\n")
            log.error(f"{tml_type} '{tml.name}' failed to import, ThoughtSpot errors:\n[fg-error]{errors}")
            continue

        if tml_import_info["response"]["status"]["status_code"] == "WARNING":
            errors = tml_import_info["response"]["status"]["error_message"].replace("<br/>", "\n")
            log.warning(f"{tml_type} '{tml.name}' partially imported, ThoughtSpot errors:\n[fg-warn]{errors}")

        if tml_import_info["response"]["status"]["status_code"] == "OK":
            log.debug(f"{tml_type} '{tml.name}' successfully imported")

    return r.json()
