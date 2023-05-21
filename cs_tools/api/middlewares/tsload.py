from __future__ import annotations

from dataclasses import dataclass
from tempfile import _TemporaryFileWrapper
from typing import Optional, Any, TYPE_CHECKING, Dict, Union
from io import BufferedIOBase, TextIOWrapper
import ipaddress as ip
import datetime as dt
import pathlib
import logging
import time
import json

from pydantic import validate_arguments
import httpx

from cs_tools._compat import TypedDict
from cs_tools.updater import CSToolsVirtualEnvironment
from cs_tools.errors import TSLoadServiceUnreachable, InsufficientPrivileges
from cs_tools.types import GroupPrivilege, RecordsFormat
from cs_tools.types import GUID as CycleID
from cs_tools.const import FMT_TSLOAD_TRUE_FALSE, FMT_TSLOAD_DATETIME, FMT_TSLOAD_TIME, FMT_TSLOAD_DATE
from cs_tools import utils

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


class CachedRedirectInfo(TypedDict):
    dataload_initialize: dt.datetime
    host: ip.IPv4Address
    port: int = 8442


@dataclass
class TSLoadNodeRedirectCache:
    # DEV NOTE: @boonhapus, 2023/01/15
    #
    #   The Falcon tsload API is parallelized across nodes, but lives at a separate port
    #   from standard ThoughtSpot services. This is because the service is responsible
    #   for (potentially very heavy) file loading. The cache will help manage
    #   redirection across CS Tools sessions.
    #
    cache_fp: pathlib.Path = CSToolsVirtualEnvironment().app_dir / ".cache/tsload-node-redirect-by-cycle-id.json"

    def __post_init__(self):
        self.cache_fp.parent.mkdir(parents=True, exist_ok=True)
        self.cache_fp.touch(exist_ok=True)
        self._remove_old_data()

    def load(self) -> Dict[CycleID, CachedRedirectInfo]:
        text = self.cache_fp.read_text()
        return json.loads(text) if text else {}

    def dump(self, data: Dict[CycleID, CachedRedirectInfo]) -> None:
        text = json.dumps(data, indent=4)
        self.cache_fp.write_text(text)

    def _remove_old_data(self) -> None:
        DAYS_TO_KEEP = 10 * 86400
        NOW = dt.datetime.utcnow().timestamp()

        keep = {}

        for cycle_id, redirect_info in self.load().items():
            init_ts = redirect_info.get("dataload_initialize") or redirect_info.get("load_datetime")

            # if the format is not known
            if init_ts is None:
                continue

            if (NOW - init_ts) <= DAYS_TO_KEEP:
                keep[cycle_id] = redirect_info

        self.dump(keep)

    def get_for(self, cycle_id: CycleID) -> Optional[CachedRedirectInfo]:
        for existing_cycle_id, redirect_info in self.load().items():
            if cycle_id == existing_cycle_id:
                return redirect_info

        return

    def set_for(self, cycle_id: CycleID, *, redirect_info: CachedRedirectInfo) -> None:
        data = self.load()
        data[cycle_id] = redirect_info
        self.dump(data)


class TSLoadMiddleware:
    """
    Wrapper around the Remote Data service APIs.

    Further reading:
      TQL ::::: https://docs.thoughtspot.com/software/latest/tql-service-api-ref
      TSLOAD :: https://docs.thoughtspot.com/software/latest/tsload-connector
      TSLOAD :: https://docs.thoughtspot.com/software/latest/tsload-api
    """

    # DEV NOTE: @boonhapus, 2023/01/15
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ARE RUNNING INTO ISSUES USING THIS SERVICE? ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 1. START HERE  https://docs.thoughtspot.com/software/latest/tsload-connector#_setting_up_your_cluster
    #
    # 2. Ignore the dataservice load balancer and submit data loads to the serving node.
    #
    #    .uplaod() and .status() have a keyword argument `ignore_node_redirect` which
    #    will skip redirection and attempt to load to the serving node.
    #
    #    If thie customer is running a load balancer, this would mean we're attempting
    #    these API calls directly there. If the customer's IPSec team has a path
    #    whitelist, then you'll want to proceed to 3.
    #
    # 3. If the customer has a load balancer sitting in front of ThoughtSpot, they will
    #    need to configure their listener rules to do both of..
    #
    #    - forward GET, POST
    #           on PATH ts_dataservice/v1/public/*
    #           to <TS-NODE-IPs> on PORT 8442
    #
    #    - allow files to the above (eg. content-type of "multipart/form-data" )
    #      https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Type
    #
    #
    # 4. Turn off the dataservice load balancer AND use `ignore_node_redirect`
    #
    #    !!!!! Here be dragons. Thou art forewarned.
    #
    #    running these can break ThoughtSpot DataFlow
    #
    #    tscli --adv service add-gflag etl_http_server.etl_http_server etl_server_enable_load_balancer false
    #    tscli --adv service add-gflag etl_http_server.etl_http_server etl_server_always_expose_node_ip true
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    def __init__(self, ts: ThoughtSpot):
        self.ts = ts
        self._cache_fp = TSLoadNodeRedirectCache()

    def _check_for_redirect_auth(self, cycle_id: CycleID) -> None:
        """
        Attempt a login.

        By default, the tsload service API sits behind a load balancer. When we first
        init a new load cycle, the balancer will respond with the proper node (if
        applicable) to submit file uploads to. If that node is not the main node, then
        we will be required to authorize again.
        """
        redirect_info = self._cache_fp.get_for(cycle_id)

        if redirect_info is not None:
            redirect_url = self.ts.api.session.base_url.copy_with(host=redirect_info["host"], port=redirect_info["port"])
            self.ts.api._redirected_url_due_to_tsload_load_balancer = redirect_url

            log.debug(f"redirecting to: {redirect_url}")
            self.ts.api.dataservice_dataload_session(
                username=self.ts.config.auth["frontend"].username,
                password=utils.reveal(self.ts.config.auth["frontend"].password).decode(),
            )

    def _check_privileges(self) -> None:
        """
        Determine if the user has necessary Data Manager privileges.
        """
        REQUIRED = set([GroupPrivilege.can_administer_thoughtspot, GroupPrivilege.can_manage_data])

        if not set(self.ts.me.privileges).intersection(REQUIRED):
            raise InsufficientPrivileges(user=self.ts.me, service="remote TQL", required_privileges=", ".join(REQUIRED))

    @validate_arguments(config=dict(arbitrary_types_allowed=True))
    def upload(
        self,
        fd: Union[BufferedIOBase, TextIOWrapper, _TemporaryFileWrapper],
        *,
        database: str,
        table: str,
        schema_: str = "falcon_default_schema",
        empty_target: bool = True,
        max_ignored_rows: int = 0,
        date_format: str = FMT_TSLOAD_DATE,
        date_time_format: str = FMT_TSLOAD_DATETIME,
        time_format: str = FMT_TSLOAD_TIME,
        skip_second_fraction: bool = False,
        field_separator: str = "|",
        null_value: str = "",
        boolean_representation: str = FMT_TSLOAD_TRUE_FALSE,
        has_header_row: bool = False,
        escape_character: str = '"',
        enclosing_character: str = '"',
        flexible: bool = False,
        # not related to Remote TSLOAD API
        ignore_node_redirect: bool = False,
        http_timeout: int = 60.0,
    ) -> RecordsFormat:
        """
        Load a file via tsload on a remote server.

        Defaults to tsload command of:
            tsload --source_file <fp>
                   --target_database <target_database>
                   --target_schema 'falcon_default_schema'
                   --target_table <target_table>
                   --max_ignored_rows 0
                   --date_time_format '%Y-%m-%d %H:%M:%S'
                   --field_separator '|'
                   --null_value ''
                   --boolean_representation True_False
                   --escape_character '"'
                   --enclosing_character '"'
                   --empty_target

        For further information on tsload, please refer to:
          https://docs.thoughtspot.com/software/latest/tsload-connector
          https://docs.thoughtspot.com/software/latest/tsload-api

        Parameters
        ----------
        fd : BufferedIOBase
          an open file descriptor

        ignore_node_redirect : bool  [default: False]
          whether or not to ignore node redirection

        **tsload_options

        Returns
        -------
        cycle_id
          unique identifier for this specific file load

        Raises
        ------
        TSLoadServiceUnreachable
          raised when the tsload api service is not reachable
        """
        self._check_privileges()

        flags = {
            "target": {"database": database, "schema": schema_, "table": table},
            "format": {
                "field_separator": field_separator,
                "enclosing_character": enclosing_character,
                "escape_character": escape_character,
                "null_value": null_value,
                "date_time": {
                    "date_time_format": date_time_format,
                    "date_format": date_format,
                    "time_format": time_format,
                    "skip_second_fraction": skip_second_fraction,
                },
                "boolean": {
                    "true_format": boolean_representation.split("_")[0],
                    "false_format": boolean_representation.split("_")[1],
                },
                "has_header_row": has_header_row,
                "flexible": flexible,
            },
            "load_options": {"empty_target": empty_target, "max_ignored_rows": max_ignored_rows},
        }

        try:
            r = self.ts.api.dataservice_dataload_initialize(data=flags, timeout=http_timeout)
        except httpx.HTTPStatusError as e:
            raise TSLoadServiceUnreachable(
                http_error=e,
                tsload_command=(
                    # these all on the same line in the error messag
                    f"tsload "
                    f"--source_file {fd.name} "
                    f"--target_database {database} "
                    f"--target_schema {schema_} "
                    f"--target_table {table} "
                    f"--max_ignored_rows {max_ignored_rows} "
                    f'--date_format "{FMT_TSLOAD_DATE}" '
                    f'--time_format "{FMT_TSLOAD_TIME}" '
                    f'--date_time_format "{FMT_TSLOAD_DATETIME}" '
                    f'--field_separator "{field_separator}" '
                    f'--null_value "{null_value}" '
                    f"--boolean_representation {boolean_representation} "
                    f'--escape_character "{escape_character}" '
                    f'--enclosing_character "{enclosing_character}" '
                    + ("--empty_target " if empty_target else "--noempty_target ")
                    + ("--has_header_row " if has_header_row else "")
                    + ("--skip_second_fraction " if skip_second_fraction else "")
                    + ("--flexible" if flexible else ""),
                ),
            )

        data = r.json()

        if "node_address" in data:
            self._cache_fp.set_for(data["cycle_id"], redirect_info=data["node_address"])

        if not ignore_node_redirect:
            self._check_for_redirect_auth(data["cycle_id"])

        self.ts.api.dataservice_dataload_start(cycle_id=data["cycle_id"], fd=fd, timeout=http_timeout)
        self.ts.api.dataservice_dataload_commit(cycle_id=data["cycle_id"])
        return data["cycle_id"]

    @validate_arguments
    def status(
        self, cycle_id: CycleID, *, ignore_node_redirect: bool = False, wait_for_complete: bool = False
    ) -> Dict[str, Any]:
        """
        Get the status of a previously started data load.

        Parameters
        ----------
        cycle_id : CycleID
          data load to check on

        ignore_node_redirect : bool  [default: False]
          whether or not to ignore node redirection

        wait_for_complete: bool  [default: False]
          poll the load server until it responds with OK or ERROR
        """
        self._check_privileges()

        if not ignore_node_redirect:
            self._check_for_redirect_auth(cycle_id)

        while True:
            r = self.ts.api.dataservice_dataload_status(cycle_id=cycle_id)
            data = r.json()

            if not wait_for_complete:
                break

            if data["internal_stage"] == "DONE":
                break

            if data["status"]["message"] != "OK":
                break

            log.debug(f"data load status:\n{data}")
            time.sleep(1)

        return data

    # @validate_arguments
    # def bad_records(self, cycle_id: str) -> RecordsFormat:
    #     """
    #     """
    #     r = self.ts.api.ts_dataservice.load_params(cycle_id)
    #     params = r.json()
    #     print(params)
    #     raise

    #     r = self.ts.api.ts_dataservice.bad_records(cycle_id)
    #     r.text
