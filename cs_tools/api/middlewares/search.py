from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import datetime as dt
import logging

from cs_tools.api import _utils
from cs_tools.errors import AmbiguousContentError, ContentDoesNotExist

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot
    from cs_tools.types import TableRowsFormat

log = logging.getLogger(__name__)


def _fix_for_scal_101507(row: TableRowsFormat) -> TableRowsFormat:
    # BUG: SCAL-101507
    #
    # DATE_TIME formatted columns return data in the format below. This fixes that.
    #
    # "data": [ {"Timestamp": {"v":{"s":1625759921}} ]
    #
    for i, value in enumerate(row):
        if isinstance(value, dict) and value["v"]:
            try:
                row[i] = value["v"]["s"]
            except Exception:
                log.warning(f"unexpected value in search-data response: {value}")

    return row


def _to_records(columns: list[str], rows: list[TableRowsFormat]) -> list[TableRowsFormat]:
    return [dict(zip(columns, _fix_for_scal_101507(row))) for row in rows]


def _cast(data: list[TableRowsFormat], headers_to_types: dict[str, str]) -> list[TableRowsFormat]:
    """
    Cast data coming back from Search API to their intended column types.
    """
    TS_TO_PY_TYPES = {
        "VARCHAR": str,
        "DOUBLE": float,
        "FLOAT": float,
        "BOOL": bool,
        "INT32": int,
        "INT64": int,
        "DATE": dt.date.fromtimestamp,
        "DATE_TIME": dt.datetime.fromtimestamp,
        "TIMESTAMP": float,
    }

    _logged = {}
    column_names = sorted(headers_to_types.keys(), key=len, reverse=True)

    for row in data:
        for column, value in row.items():
            # no need to cast a NULL..
            if value is None:
                continue

            try:
                # "column" or "total {column}" <-- any aggregation
                column_name = column if column in column_names else next(c for c in column_names if c in column)
                column_type = headers_to_types[column_name]
                cast_as_type = TS_TO_PY_TYPES[column_type]

            # ON EITHER ERROR, we'll cast to string, but only log it once per column..
            except (StopIteration, KeyError) as e:
                if isinstance(e, StopIteration):
                    msg = f"could not match column [yellow]{column}[/]"

                if isinstance(e, KeyError):
                    msg = f"could not find suitable column type for [yellow]{column}[/]=[blue]{column_type}[/]"

                if column not in _logged:
                    log.warning(f"{msg}, using VARCHAR")

                _logged[column] = 1
                cast_as_type = str

            row[column] = cast_as_type(value)

    return data


class SearchMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    # DEVNOTE:
    #   if we want to expose Search Answers interface somehow in the future,
    #   this is the way we'd do it. Usage would look something like
    #   ts.search.answers(...) and ts.search.data(query, worksheet='...')
    #
    # def data(query, worksheet=None, ...)
    # def answers(...)
    #
    #   ... right now we use __call__ so the UX is nicer.
    #

    def __call__(
        self,
        query: str,
        *,
        worksheet: Optional[str] = None,
        table: Optional[str] = None,
        view: Optional[str] = None,
        sample: bool = -1,
    ) -> TableRowsFormat:
        """
        Search a data source.

        Columns must be surrounded by square brackets. Search-level formulas
        are not currently supported, but a formula as part of a data source is.

        There is a hard limit of 100K rows extracted for any given Search.

        Further reading:
          https://docs.thoughtspot.com/software/latest/search-data-api
          https://docs.thoughtspot.com/software/latest/search-data-api#components
          https://docs.thoughtspot.com/software/latest/search-data-api#_limitations_of_search_query_api

        Parameters
        ----------
        query : str
          the ThoughtSpot Search to issue against a data source

        worksheet, table, view : str
          name or GUID of a data source to search against - these keywords are
          mutually exclusive

        Returns
        -------
        data : TableRowsFormat
          search result in data records format

        Raises
        ------
        TypeError
          raised when providing no input, or too much input to mutually
          exclusive keyword-arguments: worksheet, table, view

        ContentDoesNotExist
          raised when a worksheet, table, or view does not exist in the
          ThoughtSpot platform

        AmbiguousContentError
          raised when multiple worksheets, tables, or view exist in the
          platform by a single name
        """
        if (worksheet, table, view).count(None) == 3:
            raise TypeError(
                "ThoughtSpot.data.search() missing 1 of the required keyword-only "
                "arguments: 'worksheet', 'table', 'view'"
            )
        if (worksheet, table, view).count(None) != 2:
            raise TypeError(
                "ThoughtSpot.data.search() got multiple values for one of the "
                "mutually-exclusive keyword-only arguments: 'worksheet', 'table', 'view'"
            )

        guid = worksheet or table or view

        if worksheet is not None:
            friendly = "worksheet"
            subtype = "WORKSHEET"

        if table is not None:
            friendly = "system table"
            subtype = "ONE_TO_ONE_LOGICAL"

        if view is not None:
            friendly = "view"
            subtype = "AGGR_WORKSHEET"

        if not _utils.is_valid_guid(guid):
            d = self.ts.api.v1.metadata_list(
                metadata_type="LOGICAL_TABLE", subtypes=[subtype], pattern=guid, sort="CREATED", sort_ascending=True
            ).json()

            if not d["headers"]:
                raise ContentDoesNotExist(type=friendly, reason=f"No {friendly} found with the name [blue]{guid}")

            d = [_ for _ in d["headers"] if _["name"].casefold() == guid.casefold()]

            if len(d) > 1:
                raise AmbiguousContentError(type=friendly, name=guid)

            guid = d[0]["id"]

        log.debug(f"executing search on guid {guid}\n\n{query}\n")
        offset = 0
        data = []

        while True:
            r = self.ts.api.v1.search_data(
                query_string=query, data_source_guid=guid, format_type="COMPACT", batchsize=sample, offset=offset
            )

            d = r.json()
            data.extend(d.pop("data"))
            offset += d["rowCount"]

            if d["rowCount"] < d["pageSize"]:
                break

            if sample >= 0 and d["rowCount"] == d["pageSize"]:
                break

            if offset % 500_000 == 0:
                log.warning(
                    f"using the Data API to extract {offset / 1_000_000: >4,.1f}M+ "
                    f"rows is not scalable, consider adding a filter or extracting "
                    f"directly from the underlying data source instead!"
                )

        # Get the data types
        r = self.ts.api.v1.metadata_details(metadata_type="LOGICAL_TABLE", guids=[guid])
        data_types = {c["header"]["name"]: c["dataType"] for c in r.json()["storables"][0]["columns"]}

        # Cleanups
        data = _to_records(columns=d["columnNames"], rows=data)
        data = _cast(data, headers_to_types=data_types)
        return data
