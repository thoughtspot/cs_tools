from typing import Any, Dict, List
import datetime as dt
import logging
import json

from pydantic import validate_arguments
import httpx

from cs_tools.errors import CSToolsError, AmbiguousContentError, ContentDoesNotExist
from cs_tools.api import util


log = logging.getLogger(__name__)
DB_ROW = Dict[str, Any]


def _fix_for_scal_101507(row: List[Dict[str, Any]]) -> List[DB_ROW]:
    # BUG: SCAL-101507
    #
    # DATE_TIME formatted columns return data in the format below. This fixes that.
    #
    # "data": [ {"Timestamp": {"v":{"s":1625759921}} ]
    #
    for i, value in enumerate(row):
        if isinstance(value, dict) and value['v']:
            try:
                row[i] = value['v']['s']
            except Exception:
                log.warning(f'unexpected value in search-data response: {value}')

    return row


def _to_records(columns: List[str], rows: List[DB_ROW]) -> List[DB_ROW]:
    return [dict(zip(columns, _fix_for_scal_101507(row))) for row in rows]


def _cast(data: List[DB_ROW], types: Dict[str, str]) -> List[DB_ROW]:
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
    column_names = list(sorted(types.keys(), key=len, reverse=True))

    for row in data:
        for key in row:
            try:
                column_name = key if key in column_names else next(c for c in column_names if c in key)
                column_type = types[column_name]
                python_type = TS_TO_PY_TYPES[column_type]

            except (StopIteration, KeyError) as e:
                if isinstance(e, StopIteration):
                    msg = f"could not match column [yellow]{key}[/]"

                if isinstance(e, KeyError):
                    msg = f"could not find suitable column type for [yellow]{key}[/]=[blue]{column_type}[/]"

                if key not in _logged:
                    log.warning(f"{msg}, using VARCHAR")

                _logged[key] = 1
                python_type = str

            row[key] = python_type(row[key])

    return data


class SearchMiddleware:
    """
    """
    def __init__(self, ts):
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

    @validate_arguments
    def __call__(
        self,
        query: str,
        *,
        worksheet: str = None,
        table: str = None,
        view: str = None,
        sample: bool = -1
    ) -> List[Dict[str, Any]]:
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
        data : List[Dict[str, Any]]
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

        if not util.is_valid_guid(guid):
            d = self.ts._rest_api._metadata.list(
                       type='LOGICAL_TABLE',
                       subtypes=[subtype],
                       pattern=guid,
                       sort='CREATED',
                       sortascending=True
                   ).json()

            if not d['headers']:
                raise ContentDoesNotExist(
                    type=friendly,
                    reason=f"No {friendly} found with the name [blue]{guid}"
                )

            d = [_ for _ in d['headers'] if _['name'].casefold() == guid.casefold()]

            if len(d) > 1:
                raise AmbiguousContentError(type=friendly, name=guid)

            guid = d[0]['id']

        log.debug(f'executing search on guid {guid}\n\n{query}\n')
        offset = 0
        data = []

        while True:
            try:
                r = self.ts._rest_api.data.searchdata(
                        query_string=query,
                        data_source_guid=guid,
                        formattype='COMPACT',
                        batchsize=sample,
                        offset=offset
                    )
            except httpx.HTTPStatusError as e:
                log.debug(e, exc_info=True)
                err = e.response.json()
                errors = [msg for msg in json.loads(err["debug"]) if msg]
                query = query.replace('[', r'\[')
                raise CSToolsError(
                    error="\n".join(errors),
                    mitigation=(
                        f"Double check, does this query apply to [blue]{worksheet or table or view}[/]?"
                        f"\n\nSearch terms\n[blue]{query}"
                    )
                )

            d = r.json()
            data.extend(d.pop('data'))
            offset += d['rowCount']

            if d['rowCount'] < d['pageSize']:
                break

            if sample >= 0 and d['rowCount'] == d['pageSize']:
                break

            if offset % 500_000 == 0:
                log.warning(
                    f'using the Data API to extract {offset / 1_000_000: >4,.1f}M+ '
                    f'rows is not a scalable practice, consider adding a filter or '
                    f'extracting directly from the underlying data source instead!'
                )

        # Get the data types
        r = self.ts._rest_api.metadata.details(type="LOGICAL_TABLE", id=[guid])
        data_types = {c["header"]["name"]: c["dataType"] for c in r.json()["storables"][0]["columns"]}

        # Cleanups
        data = _to_records(columns=d["columnNames"], rows=data)
        data = _cast(data, types=data_types)
        return data
