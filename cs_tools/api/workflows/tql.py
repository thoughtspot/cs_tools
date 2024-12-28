from __future__ import annotations

from typing import Any
import datetime as dt
import json
import logging

from cs_tools import types
from cs_tools.api.client import RESTAPIClient

log = logging.getLogger(__name__)


def _cast_to_records(row_values: list[Any], *, column_info: list[dict]) -> list[types.APIResult]:
    """Pair up column values to their names, and clean up the TIMESTAMP representation."""
    TS_TO_PY_TYPE_MAPPING: dict[types.InferredDataType, type] = {
        "VARCHAR": str,
        "DOUBLE": float,
        "FLOAT": float,
        "BOOL": bool,  # type: ignore[dict-item]
        "INT": int,  # type: ignore[dict-item]
        "BIGINT": int,  # type: ignore[dict-item]
        "DATE": dt.date.fromtimestamp,  # type: ignore[dict-item]
        "DATE_TIME": dt.datetime.fromtimestamp,  # type: ignore[dict-item]
        "TIMESTAMP": float,
    }

    full: list[types.APIResult] = []

    for row in row_values:
        for idx, value in enumerate(row.pop("v")):
            # FETCH THE COLUMN INFO
            column_name = column_info[idx]["name"]
            column_type = column_info[idx]["type"]
            typing_cast = TS_TO_PY_TYPE_MAPPING[column_type]

            # PROCESS THE ROW FOR ANY TIMESTAMP / DATE_TIME / DATE VALUES
            value_clean = value["s"] if isinstance(value, dict) else value

            # SET THE VALUE OF THE COMPACT ROW-CELL, AS A CLEANED FULL VERSION
            row[column_name] = typing_cast(value_clean)

        full.append(row)

    return full


async def query(
    statement: str,
    *,
    falcon_context: types.TQLQueryContext | None = None,
    record_offset: int = 0,
    record_size: int = 5_000_000,
    field_delimiter: str = "|",
    record_delimiter: str = "\n",
    null_representation: str = "{null}",
    skip_cache: bool = False,
    allow_unsafe: bool = False,
    query_options: dict | None = None,
    advanced_options: dict | None = None,
    http: RESTAPIClient,
) -> types.APIResult:
    """Wraps ts_dataservice/query in a V2.0-like interface."""
    # Further reading on what can be passed to `data`
    #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_inputoutput_structure
    #   https://docs.thoughtspot.com/software/latest/tql-service-api-ref.html#_request_body
    data = {
        "context": falcon_context or {"database": "", "schema": "falcon_default_schema", "server_schema_version": -1},
        "query": {"statement": statement if statement.endswith(";") else f"{statement};"},
        "options": {
            # FOR CONFIGURING HOW THE QUERY IS EXECUTED.
            "query_options": {
                "pagination": {
                    "start": record_offset,
                    "size": record_size,
                },
                "query_results_apply_top_row_count": 50,
                **(query_options or {}),
            },
            # FOR CONFIGURING HOW THE RESULTS ARE RETURNED.
            "formatting_options": {
                "field_separator": field_delimiter,
                "row_separator": record_delimiter,
                "null_string": null_representation,
                "date_format": {
                    "format_date_as_epoch": True,  # as millis
                },
            },
            # FOR CONFIGURING TQL SCRIPT CONTEXT. (unused)
            # "scripting_options": {},
            # FOR CONFIGURING HOW THE RESULTS ARE DISPLAYED.
            "adv_options": {
                "skip_cache": skip_cache,
                "allow_unsafe": allow_unsafe,
                "continue_execution_on_error": False,
                **(advanced_options or {}),
            },
        },
    }

    r = await http.v1_dataservice_query(**data)
    r.raise_for_status()

    d: types.APIResult = {
        "prev_falcon_context": falcon_context,
        "curr_falcon_context": None,
        "data": [],
        "message": {"severity": "DEBUG", "content": ""},
        "original": [],
    }

    # DEV NOTE: @boonhapus, 2024/12/15
    # WE USE json.loads(r.iterlines()) INSTEAD OF r.json() BECAUSE THE API RETURNS JSON-LINES.
    for result in r.iter_lines():
        _ = json.loads(result)

        d["original"].append(_)

        if _IS_INTERACTIVE := "interactive_question" in _["result"]:
            ...  # TODO ...

        if _IS_DATA_RESULT := ("table" in _["result"] and "rows" in _["result"]["table"]):
            d["data"] = _cast_to_records(_["result"]["table"]["rows"], column_info=_["result"]["table"]["headers"])

        if _IS_CTX_MESSAGE := "message" in _["result"]:
            d["curr_falcon_context"] = _["result"]["final_context"]

            for message in _["result"]["message"]:
                if message["value"].strip() == "Statement executed successfully.":
                    continue

                severity_level = max(
                    logging.getLevelName(message["type"]),
                    logging.getLevelName(d["message"]["severity"]),
                )

                d["message"]["severity"] = logging.getLevelName(severity_level)
                d["message"]["content"] += message["value"]

    return d
