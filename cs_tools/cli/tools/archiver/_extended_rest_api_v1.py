from __future__ import annotations

from typing import TYPE_CHECKING
import json

if TYPE_CHECKING:
    import httpx

    from cs_tools.types import GUID, MetadataObjectType


def metadata_delete(ts_client: httpx.Client, *, metadata_type: MetadataObjectType, guids: list[GUID]) -> httpx.Response:
    """
    DELETE metadata
    """
    d = {"type": metadata_type, "id": json.dumps(guids)}
    r = ts_client.post("callosum/v1/metadata/delete", data=d)
    return r
