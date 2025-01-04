from __future__ import annotations

from typing import Any
import datetime as dt
import logging

from cs_tools import _types
from cs_tools.api.client import RESTAPIClient
from cs_tools.api.workflows import metadata

__all__ = ("search",)

log = logging.getLogger(__name__)


def _convert_compact_to_full(compact: list[Any], *, column_names: list[str]) -> _types.APIResult:
    """Pair up column values to their names, and clean up the TIMESTAMP representation."""
    full: _types.APIResult = {}

    for idx, value in enumerate(compact):
        # FETCH THE COLUMN NAME
        column_name = column_names[idx]

        # PROCESS THE ROW FOR ANY TIMESTAMP / DATE_TIME / DATE VALUES
        value_clean = value["v"]["s"] if isinstance(value, dict) else value

        # SET THE VALUE OF THE COMPACT ROW-CELL, AS A CLEANED FULL VERSION
        full[column_name] = value_clean

    return full


def _cast(data_rows: _types.TableRowsFormat, *, column_info: dict[str, _types.InferredDataType]) -> _types.TableRowsFormat:  # noqa: E501
    """Cast data coming back from Search API to their intended column _types."""
    TS_TO_PY_TYPE_MAPPING: dict[_types.InferredDataType, type] = {
        "VARCHAR": str,
        "CHAR": str,
        "DOUBLE": float,
        "FLOAT": float,
        "BOOL": bool,
        "INT32": int,
        "INT64": int,
        "DATE": dt.date.fromtimestamp,  # type: ignore[dict-item]
        "DATE_TIME": dt.datetime.fromtimestamp,  # type: ignore[dict-item]
        "TIMESTAMP": float,
    }

    LOGGED_TYPE_MISSING_WARNING: dict[str, bool] = {}

    for row in data_rows:
        for column, value in row.items():
            # CASTING NULL IS A NOOP
            if value is None:
                continue

            try:
                # "column" or "total {column}" <-- any aggregation
                column_name = column if column in column_info else next(c for c in column_info if c in column)
                column_type = column_info[column_name]
                cast_as_type = TS_TO_PY_TYPE_MAPPING[column_type]

            except (StopIteration, KeyError) as e:
                if column not in LOGGED_TYPE_MISSING_WARNING and isinstance(e, StopIteration):
                    log.warning(f"Could not match column '{column}' to a LOGICAL_TABLE column.")

                if column not in LOGGED_TYPE_MISSING_WARNING and isinstance(e, KeyError):
                    log.warning(f"Could not find a column type to infer for '{column}' with type '{column_type}'.")

                LOGGED_TYPE_MISSING_WARNING[column] = True
                cast_as_type = str

            row[column] = cast_as_type(value)

    return data_rows


async def search(
    worksheet: _types.ObjectIdentifier, *, query: str, batch_size: int = 100_000, http: RESTAPIClient
) -> _types.TableRowsFormat:
    """
    Perform a Search against a specific Worksheet.

    Further reading:
        https://developers.thoughtspot.com/docs/fetch-data-and-report-apis#_search_data_api
    """
    # FOR POST-PROCESSING DATA VALUES TO CONVERT TO THEIR APPROPRIATE DATA TYPES
    d = await metadata.fetch_one(identifier=worksheet, metadata_type="LOGICAL_TABLE", include_details=True, http=http)
    worksheet_guid = d["metadata_header"]["id"]
    worksheet_column_info = {column["header"]["name"]: column["dataType"] for column in d["metadata_detail"]["columns"]}

    data: _types.TableRowsFormat = []

    log.debug(f"Executing Search on '{worksheet}'\n\n{query}\n")

    # IT'S IMPOSSIBLE TO KNOW HOW MANY ROWS WILL BE RETURNED FROM A GIVEN SEARCH
    # BEFOREHAND SO WE MUST POLL THE API UNTIL ALL ROWS HAVE BEEN RETRIEVED.
    while True:
        r = await http.search_data(
            logical_table_identifier=worksheet_guid,
            query_string=query,
            # DEV NOTE: @boonhapus, 2024/11/19
            # WE USE `COMPACT` INSTEAD OF FULL BECAUSE IT'S FASTER AND NULL VALUES DO NOT GET DROPPED FROM THE RESPONSE.
            data_format="COMPACT",
            record_offset=len(data),
            record_size=batch_size,
        )

        r.raise_for_status()

        d = r.json()

        for data_row in d["contents"][0]["data_rows"]:
            data.append(_convert_compact_to_full(data_row, column_names=d["contents"][0]["column_names"]))

        # IF THERE ARE NO MORE ROWS TO RETRIEVE, WE'LL STOP HERE.
        if len(d["contents"][0]["data_rows"]) < batch_size:
            break

        # Warn the user if the returned data exceeds the 1M row threshold
        if len(data) % 500_000 == 0:
            log.warning(
                f"Using the Search Data API to extract {len(data) / 1_000_000: >4,.1f}M+ rows is not scalable, "
                f"consider adding a filter or extracting directly from the underlying data source instead!"
            )

    data = _cast(data, column_info=worksheet_column_info)

    return data
