from typing import Any, Dict, List
import datetime as dt
import logging
import json

from pydantic import validate_arguments
import httpx

from cs_tools.api.util import stringified_array
from cs_tools.data.enums import GUID


log = logging.getLogger(__name__)


class User:
    """
    Public User Services.
    """
    def __init__(self, rest_api):
        self.rest_api = rest_api

    def list(self) -> httpx.Response:
        """
        Fetch users and groups.
        """
        r = self.rest_api.request('GET', 'user/list', privacy='public')
        return r

    @validate_arguments
    def transfer_ownership(
        self,
        fromUserName: str,
        toUserName: str,
        objectid: List[GUID] = None
    ) -> httpx.Response:
        """
        Transfer ownership of all objects from one user to another.
        """
        r = self.rest_api.request(
                'POST',
                'user/transfer/ownership',
                privacy='public',
                params={
                    'fromUserName': fromUserName,
                    'toUserName': toUserName,
                    # technically not available until ts7.sep.cl-109 or greater, but
                    # query parameters don't usually cause 4xx or 5xx errors
                    'objectid': stringified_array(objectid or ())
                }
            )
        return r

    @validate_arguments
    def sync(
        self,
        principals: List[Dict[str, Any]],
        applyChanges: bool = False,
        removeDeleted: bool = True,
        password: str = None
    ) -> httpx.Response:
        """
        Api to synchronize principal from external system with ThoughtSpot system
        """
        dir_ = self.rest_api._config.temp_dir / 'user_syncs'
        dir_.mkdir(parents=True, exist_ok=True)

        now = dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        fp = dir_ / f'principals-{now}.json'

        with fp.open('w') as f:
            log.debug(f'writing principals (before sync) to {fp}')
            json.dump(principals, f, indent=4)

        r = self.rest_api.request(
                'POST',
                'user/sync',
                privacy='public',
                files={'principals': ('principals.json', fp.open('rb'), 'application/json')},
                data={
                    'applyChanges': applyChanges,
                    'removeDeleted': removeDeleted,
                    'password': password
                }
            )
        return r
