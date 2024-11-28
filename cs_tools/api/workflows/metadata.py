from __future__ import annotations

from collections.abc import Iterable
import asyncio
import logging

import awesomeversion
import httpx

from cs_tools import types, utils
from cs_tools.api.client import RESTAPIClient
from cs_tools.api.workflows.utils import batched

__all__ = ("fetch", "fetch_all", "permissions")

log = logging.getLogger(__name__)


async def fetch_all(
    object_types: Iterable[types.APIObjectType], *, http: RESTAPIClient, record_size: int = 5_000, **search_options
) -> list[types.APIResult]:
    """Wraps metadata/search fetching all objects of the given type and exhausts the pagination."""
    results: list[types.APIResult] = []
    tasks: list[asyncio.Task] = []

    async with utils.BoundedTaskGroup(max_concurrent=len(list(object_types))) as g:
        for object_type in object_types:
            search_options["guid"] = ""
            search_options["metadata"] = [{"type": object_type}]
            coro = batched(http.metadata_search, record_size=record_size, **search_options)
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
    CONCURRENCY_MAGIC_NUMBER = 15  # Why? No particular reason, but it's far less than RESTAPIClient.

    results: list[types.APIResult] = []
    tasks: list[asyncio.Task] = []

    async with utils.BoundedTaskGroup(max_concurrent=CONCURRENCY_MAGIC_NUMBER) as g:
        for metadata_type, guids in typed_guids.items():
            for guid in guids:
                # NOTE: WE DON'T NEED utils.batched BECAUSE WE ARE ONLY ASKING FOR A SINGLE OBJECT
                search_options["guid"] = ""
                search_options["metadata"] = [{"type": metadata_type, "identifier": guid}]
                coro = http.metadata_search(record_size=record_size, **search_options)
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


async def permissions(
    typed_guids: dict[types.APIObjectType, Iterable[types.GUID]],
    *,
    compat_ts_version: awesomeversion.AwesomeVersion,
    record_size: int = -1,
    http: RESTAPIClient,
    **permission_options,
) -> list[types.APIResult]:
    """Wraps security/metadata/fetch-permissions fetching specific objects and exhausts the pagination."""
    CONCURRENCY_MAGIC_NUMBER = 5  # Why? No particular reason, but it's far less than RESTAPIClient.
    FIFTEEN_MINUTES = 60 * 15

    results: list[types.APIResult] = []
    tasks: list[asyncio.Task] = []

    async with utils.BoundedTaskGroup(max_concurrent=CONCURRENCY_MAGIC_NUMBER) as g:
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
                    c = http.v1_metadata_permissions(guid=guid, api_object_type=metadata_type, **permission_options)
                else:
                    permission_options["timeout"] = FIFTEEN_MINUTES
                    c = http.metadata_permissions(guid=guid, record_size=record_size, **permission_options)

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
