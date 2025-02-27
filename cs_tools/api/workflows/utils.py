from __future__ import annotations

from typing import Any
import logging

import httpx

log = logging.getLogger(__name__)


async def paginator(endpoint_method, *, record_size: int = 5_000, **api_options) -> list[Any]:
    """Exhaust a paginated endpoint."""
    data: list[Any] = []

    while True:
        r = await endpoint_method(**api_options, record_offset=len(data), record_size=record_size)

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            page = (len(data) // record_size) + 1
            log.error(f"Could not fetch '{endpoint_method.__name__}' on page #{page} -> {e}, see logs for details..")
            log.debug(f"Method options: {dict(**api_options, record_offset=len(data), record_size=record_size)}")
            log.debug(f"Error details: {r.text}", exc_info=True)
            break

        d = r.json()

        if not d:
            break

        data.extend(d) if isinstance(d, list) else data.append(d)

    return data
