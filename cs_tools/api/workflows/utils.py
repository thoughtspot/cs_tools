from __future__ import annotations

from typing import Any


async def paginator(endpoint_method, *, record_size: int = 5_000, **api_options) -> list[Any]:
    """Exhaust a paginated endpoint."""
    data: list[Any] = []

    while True:
        r = await endpoint_method(**api_options, record_offset=len(data), record_size=record_size)
        r.raise_for_status()
        d = r.json()

        if not d:
            break

        data.extend(d) if isinstance(d, list) else data.append(d)

    return data
