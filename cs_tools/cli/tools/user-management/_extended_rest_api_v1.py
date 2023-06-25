import httpx


def dataflow_transfer_ownership(ts_client: httpx.Client, *, from_username: str, to_username: str) -> httpx.Response:
    """
    Like /user/transfer/ownership , but for DataFlow.
    """
    d = {"fromUserName": from_username, "toUserName": to_username}
    r = ts_client.get("dataflow/diapi/transferofownership", data=d)
    return r
