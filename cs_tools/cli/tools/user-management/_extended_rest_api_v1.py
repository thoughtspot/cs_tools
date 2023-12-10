from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx


def dataflow_transfer_ownership(ts_client: httpx.Client, *, from_username: str, to_username: str) -> httpx.Response:
    """
    Like /user/transfer/ownership , but for DataFlow.
    """
    d = {"fromUserName": from_username, "toUserName": to_username}
    r = ts_client.get("dataflow/diapi/transferofownership", data=d)
    return r
