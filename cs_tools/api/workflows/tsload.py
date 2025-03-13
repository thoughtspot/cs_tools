from __future__ import annotations

from typing import Annotated, Any, Optional, TextIO
import asyncio
import datetime as dt
import json
import logging

import httpx

from cs_tools import _compat, _types, errors
from cs_tools.api.client import RESTAPIClient
from cs_tools.updater import cs_tools_venv

_LOG = logging.getLogger(__name__)


class AuthInfo(_compat.TypedDict):
    username: str
    password: str


class DataloadNodeInfo(_compat.TypedDict):
    host: str
    port: int
    began_at_utc: Annotated[str, _types.DateTimeInUTC]


class DataloadCache:
    """A tiny wrapper around the dataload cache file."""

    CACHE_LOC = cs_tools_venv.subdir(".cache") / "tsload_dataloads.json"

    @staticmethod
    def load_cycles() -> dict[_types.GUID, DataloadNodeInfo]:
        """Load dataloads from cache."""
        if not DataloadCache.CACHE_LOC.exists():
            return {}

        text = DataloadCache.CACHE_LOC.read_text()
        data = json.loads(text)
        return data

    @staticmethod
    def update(cycle_id: _types.GUID, node_info: dict[str, Any]) -> None:
        """Set a dataload IP Address redirect."""
        LOOPBACK = "127.0.0.1"

        if node_info.get("host", LOOPBACK) == LOOPBACK:
            return None

        data = DataloadCache.load_cycles()

        data[cycle_id] = {
            "host": node_info["host"],
            "port": node_info["port"],
            "began_at_utc": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        }

        text = json.dumps(data, indent=4)

        DataloadCache.CACHE_LOC.write_text(text)
        return None

    @staticmethod
    def fetch(cycle_id: Optional[_types.GUID]) -> Optional[DataloadNodeInfo]:
        """Fetch possible IP Address redirect for a given dataload."""
        if cycle_id is None:
            return None

        data = DataloadCache.load_cycles()

        if node_info := data.get(cycle_id, None):
            return node_info

        return None


async def upload_data(
    fd: TextIO,
    *,
    auth_info: AuthInfo,
    # DATABASE OPTIONS
    database: str,
    schema: str,
    table: str,
    # FORMAT OPTIONS
    field_separator: str = "|",
    enclosing_character: str = '"',
    escape_character: str = '"',
    null_value: str = "",
    date_time_format: str = r"%Y-%m-%d %H:%M:%S",
    date_format: str = r"%Y-%m-%d",
    time_format: str = r"%H:%M:%S",
    skip_second_fraction: bool = True,
    boolean_representation: str = "True_False",
    has_header_row: bool = True,
    flexible: bool = False,
    # LOAD_OPTIONS
    empty_target: bool = False,
    max_ignored_rows: int = 0,
    # CS TOOLS OPTIONS
    ignore_node_redirect: bool = False,
    http_timeout: Optional[int] = None,
    http: RESTAPIClient,
) -> _types.GUID:
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
    """
    assert len(boolean_representation.split("_")) == 2, "'boolean_representation' must be two options separated by a _"

    flags = {
        "target": {"database": database, "schema": schema, "table": table},
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
        r = await http.v1_dataservice_dataload_initialize(data=flags, timeout=http_timeout)
    except httpx.HTTPError as e:
        raise errors.TSLoadServiceUnreachable(httpx_error=e, file_descriptor=fd, tsload_options=flags) from None

    data = r.json()

    _LOG.info(f"Data load to Falcon initialization complete, cycle id: {data['cycle_id']}")

    if "node_address" in data:
        DataloadCache.update(cycle_id=data["cycle_id"], node_info=data["node_address"])

    if not ignore_node_redirect and (redirect := DataloadCache.fetch(cycle_id=data.get("cycle_id", None))):
        http._redirected_url_due_to_tsload_load_balancer = httpx.URL(host=redirect["host"], port=redirect["port"])  # type: ignore[attr-defined]
        # DEV NOTE: @boonhapus, 2025/01/28
        # Technically speaking, this endpoint just delegates to the AUTH SERVICE on each node, so any persistent login
        # API method should work here, it just needs to point at the redirected node. CS Tools offers multiple login
        # methods, but it's a pretty safe bet that the customer on Falcon will have a BASIC auth context.
        r = await http.v1_dataservice_dataload_session(**auth_info)
        r.raise_for_status()

    r = await http.v1_dataservice_dataload_start(cycle_id=data["cycle_id"], fd=fd, timeout=http_timeout)
    _LOG.info(f"{database}.{schema}.{table} - {r.text}")
    r.raise_for_status()

    r = await http.v1_dataservice_dataload_commit(cycle_id=data["cycle_id"])
    _LOG.info(r.text)
    r.raise_for_status()

    return data["cycle_id"]


async def wait_for_dataload_completion(
    cycle_id: _types.GUID,
    *,
    timeout: int = 300,
    http: RESTAPIClient,
) -> _types.APIResult:
    """Wait for dataload to complete."""
    start = dt.datetime.now(tz=dt.timezone.utc)

    while True:
        _LOG.info(f"Checking status of dataload {cycle_id}...")
        r = await http.v1_dataservice_dataload_status(cycle_id=cycle_id)

        status_data = r.json()

        if "code" in status_data.get("status", {}):
            break

        if (dt.datetime.now(tz=dt.timezone.utc) - start).seconds >= timeout:
            _LOG.warning(f"Reached the {timeout / 60:.1f} minute CS Tools timeout, giving up on cycle_id {cycle_id}")
            break

        _LOG.debug(status_data)
        await asyncio.sleep(5)

    _LOG.info(
        f"Cycle ID: {status_data['cycle_id']} ({status_data['status']['code']})"
        f"\nStage: {status_data['internal_stage']}"
        f"\nRows written: {status_data['rows_written']}"
        f"\nIgnored rows: {status_data['ignored_row_count']}"
    )

    if status_data["status"]["code"] == "LOAD_FAILED":
        _LOG.error(f"Failure reason\n[bold red]{status_data['status']['message']}[/]")

    if status_data.get("parsing_errors", False):
        _LOG.info(f"[fg-error]{status_data['parsing_errors']}")

    return status_data
