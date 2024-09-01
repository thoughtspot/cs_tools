from __future__ import annotations

from typing import TYPE_CHECKING

from cs_tools.api._rest_api_v1 import RESTAPIv1

if TYPE_CHECKING:
    import httpx


def periscope_sage_combined_table_info(ts_client: RESTAPIv1) -> httpx.Response:
    """
    The API call powers the Falcon Table Usage info.

    This information is only useful on ThoughtSpot Software clusters running Falcon.

    You can find the same information by going to..

       Admin >>> System >>> Table Status >>> Table Information
    """
    MIN_WAIT_10 = 60 * 10

    p = {
        # nodes = <ip-of-node>
        #   return the size of all tables on the given node
        #
        # nodes = all
        #   return the size of all tables on all nodes
        #     if table is sharded, this is the size summed across all nodes
        #     if table is replicated, this is the size on a single node
        "nodes": "all",
        # we override the callosum timeout to be 10mins in case we're on an unusually large cluster
        "callosumTimeout": MIN_WAIT_10,
    }
    r = ts_client.request(method="GET", endpoint="periscope/sage/combinedtableinfo", params=p, timeout=MIN_WAIT_10)
    return r
