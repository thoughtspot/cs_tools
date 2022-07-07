from typing import Any, Dict, List
import logging

from pydantic import validate_arguments

from cs_tools.errors import AmbiguousContentError, ContentDoesNotExist
from cs_tools.api import util


log = logging.getLogger(__name__)


def _clean_datetime(row: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # BUG: SCAL-101507
    #
    # Prior to ts7.nov.cl-1xx / 7.2.1 release, DATE_TIME formatted columns would return
    # data in the format below. This fixes that.
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
                "ThoughtSpot.search() missing 1 of the required keyword-only "
                "arguments: 'worksheet', 'table', 'view'"
            )
        if (worksheet, table, view).count(None) != 2:
            raise TypeError(
                "ThoughtSpot.search() got multiple values for one of the "
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
            r = self.ts._rest_api.data.searchdata(
                    query_string=query,
                    data_source_guid=guid,
                    formattype='COMPACT',
                    batchsize=sample,
                    offset=offset
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
                    f'using the Search API to extract >= {offset / 1_000_000: >3,.1f}M '
                    f'rows is not a scalable practice, please consider adding a filter '
                    f'or extracting records directly from the underlying data source '
                    f'instead!'
                )

        return [dict(zip(d['columnNames'], _clean_datetime(row))) for row in data]
