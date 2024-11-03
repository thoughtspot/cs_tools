from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional, Union
import datetime as dt
import ipaddress as ip
import json
import logging
import pathlib
import time

import httpx

from cs_tools._compat import TypedDict
from cs_tools.errors import InsufficientPrivileges, TSLoadServiceUnreachable
from cs_tools.types import (
    GUID as CycleID,
    GroupPrivilege,
)
from cs_tools.updater import cs_tools_venv

if TYPE_CHECKING:
    from io import TextIOWrapper
    from tempfile import _TemporaryFileWrapper

    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)
# ISO datetime format
FMT_TSLOAD_DATE = "%Y-%m-%d"
FMT_TSLOAD_TIME = "%H:%M:%S"
FMT_TSLOAD_DATETIME = f"{FMT_TSLOAD_DATE} {FMT_TSLOAD_TIME}"
FMT_TSLOAD_TRUE_FALSE = "True_False"


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
    cache_fp: pathlib.Path = cs_tools_venv.app_dir / ".cache/tsload-node-redirect-by-cycle-id.json"

    def __post_init__(self):
        self.cache_fp.parent.mkdir(parents=True, exist_ok=True)
        self.cache_fp.touch(exist_ok=True)
        self._remove_old_data()

    def load(self) -> dict[CycleID, CachedRedirectInfo]:
        text = self.cache_fp.read_text()
        return json.loads(text) if text else {}

    def dump(self, data: dict[CycleID, CachedRedirectInfo]) -> None:
        text = json.dumps(data, indent=4)
        self.cache_fp.write_text(text)

    def _remove_old_data(self) -> None:
        DAYS_TO_KEEP = 10 * 86400
        NOW = dt.datetime.now(tz=dt.timezone.utc).timestamp()

        keep = {}

        for cycle_id, redirect_info in self.load().items():
            init_ts = redirect_info.get("dataload_initialize") or redirect_info.get("load_datetime")

            # if the format is not known
            if init_ts is None:
                continue

            assert isinstance(init_ts, float)

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

    def _check_for_redirect_auth(self, *, cycle_id: CycleID) -> None:
        """
        Attempt a login.

        By default, the tsload service API sits behind a load balancer. When we first
        init a new load cycle, the balancer will respond with the proper node (if
        applicable) to submit file uploads to. If that node is not the main node, then
        we will be required to authorize again.
        """
        # fmt: off
        redirect_url  = self.ts.api.v1._redirected_url_due_to_tsload_load_balancer
        redirect_info = self._cache_fp.get_for(cycle_id)
        # fmt: on

        is_currently_on_node = redirect_url is not None and redirect_url.host == redirect_info["host"]

        if not is_currently_on_node:
            redirected = self.ts.api._session.base_url.copy_with(host=redirect_info["host"], port=redirect_info["port"])
            self.ts.api.v1._redirected_url_due_to_tsload_load_balancer = redirected

            log.info(f"The tsload API is redirecting CS Tools to node ->  {redirected}")
            self.ts.login()

    def _check_privileges(self) -> None:
        """
        Determine if the user has necessary Data Manager privileges.
        """
        REQUIRED = {GroupPrivilege.can_administer_thoughtspot, GroupPrivilege.can_manage_data}

        user = self.ts.session_context.user

        if not user.is_data_manager:
            raise InsufficientPrivileges(user=user, service="remote TQL", required_privileges=", ".join(REQUIRED))

    def upload(
        self,
        fd: Union[TextIOWrapper, _TemporaryFileWrapper],
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
        http_timeout: float = 60.0,
    ) -> CycleID:
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
            r = self.ts.api.v1.dataservice_dataload_initialize(data=flags, timeout=http_timeout)
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
            ) from None

        data = r.json()

        log.info(f"Data load to Falcon initialization complete, cycle id: {data['cycle_id']}")

        if "node_address" in data:
            self._cache_fp.set_for(data["cycle_id"], redirect_info=data["node_address"])

        if not ignore_node_redirect:
            self._check_for_redirect_auth(cycle_id=data["cycle_id"])

        r = self.ts.api.v1.dataservice_dataload_start(cycle_id=data["cycle_id"], fd=fd, timeout=http_timeout)
        log.info(f"{database}.{schema_}.{table} - {r.text}")
        r.raise_for_status()

        r = self.ts.api.v1.dataservice_dataload_commit(cycle_id=data["cycle_id"])
        log.info(r.text)
        r.raise_for_status()

        return data["cycle_id"]

    def status(self, cycle_id: CycleID, *, wait_for_complete: bool = False) -> dict[str, Any]:
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

        while True:
            r = self.ts.api.v1.dataservice_dataload_status(cycle_id=cycle_id)
            data = r.json()

            if not wait_for_complete:
                break

            if data["internal_stage"] in ("COMMITTING", "INGESTING"):
                continue

            if data["internal_stage"] == "DONE":
                break

            if "code" in data["status"] and data["status"]["code"] != "OK":
                break

            log.debug(f"data load status:\n{data}")
            time.sleep(1)

        return data
