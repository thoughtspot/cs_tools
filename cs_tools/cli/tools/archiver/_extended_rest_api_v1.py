from typing import List
import json

import httpx

from cs_tools.types import MetadataObjectType, GUID


def metadata_delete(
    ts_client: httpx.Client,
    *,
    metadata_type: MetadataObjectType,
    guids: List[GUID]
) -> httpx.Response:
    """
    DELETE metadata
    """
    d = {"type": metadata_type, "id": json.dumps(guids)}
    r = ts_client.post("callosum/v1/metadata/delete", data=d)
    return r
