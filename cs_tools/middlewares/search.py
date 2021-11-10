from typing import Any, Dict, List
import logging

from pydantic import validate_arguments

from cs_tools.errors import AmbiguousContentError, ContentDoesNotExist
from cs_tools import util


log = logging.getLogger(__name__)


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
        worksheet: str=None,
        table: str=None,
        view: str=None
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

        if not util.is_valid_guid(guid):
            d = self.ts._rest_api._metadata.list(
                       type='LOGICAL_TABLE',
                       pattern=guid,
                       sort='CREATED',
                       sortascending=True
                   ).json()

            if not d['headers']:
                raise ContentDoesNotExist(type='LOGICAL_TABLE', name=guid)

            d = [_ for _ in d['headers'] if _['name'].casefold() == guid.casefold()]

            if len(d) > 1:
                raise AmbiguousContentError(name=guid, type='LOGICAL_TABLE')

            guid = d[0]['id']

        _ = query.replace('[', '\[')
        log.debug(f"executing search: {_}\n            guid: {guid}")

        d = self.ts._rest_api.data.searchdata(
                query_string=query,
                data_source_guid=guid,
                formattype='FULL'
            ).json()

        if d['samplingRatio'] < 1:
            log.warning(f"not all data was included as part of this search, sampling ratio: {d['samplingRatio']}")

        # normalize datatime-based data
        data = []

        for row in d['data']:
            _data = {}

            for col_name, col_data in row.items():
                if isinstance(col_data, dict) and col_data['v']:
                    col_data = col_data['v']['s']

                _data[col_name] = col_data

            data.append(_data)
        # /

        return data
