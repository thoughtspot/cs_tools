from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Union, List
import logging

from pydantic import validate_arguments

from cs_tools.errors import ContentDoesNotExist
from cs_tools.types import MetadataCategory, RecordsFormat, GUID
from cs_tools.utils import chunks
from cs_tools.api import _utils

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


class LogicalTableMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts
        self.cache = {"calendar_type": {}, "currency_type": {}}

    @validate_arguments
    def all(
        self,
        *,
        tags: Union[str, List[str]] = None,
        category: MetadataCategory = MetadataCategory.all,
        hidden: bool = False,
        exclude_system_content: bool = True,
        chunksize: int = 500,
    ) -> RecordsFormat:
        """
        Get all tables in ThoughtSpot.

        Parameters
        ----------
        tags : str, or list of str
          tables which are specifically tagged or stickered

        category : str = 'all'
          one of: 'all', 'yours', or 'favorites'

        exclude_system_content : bool = True
          whether or not to include system-generated tables

        Returns
        -------
        tables : list[Dict[str, Any]]
          all answer headers
        """
        if isinstance(tags, str):
            tags = [tags]

        tables = []

        while True:
            r = self.ts.api.metadata_list(
                metadata_type="LOGICAL_TABLE",
                category=category,
                tag_name=tags,
                show_hidden=hidden,
                batchsize=chunksize,
                offset=len(tables),
            )

            data = r.json()
            to_extend = data["headers"]

            if exclude_system_content:
                to_extend = [table for table in to_extend if table.get("authorName") not in _utils.SYSTEM_USERS]

            tables.extend(to_extend)

            if not tables:
                info = {
                    "incl": "exclude" if exclude_system_content else "include",
                    "category": category,
                    "tags": ", ".join(tags),
                    "reason": (
                        "Zero {type} matched the following filters"
                        "\n"
                        "\n  - [blue]{category.value}[/] {type}"
                        "\n  - [blue]{incl}[/] admin-generated {type}"
                        "\n  - with tags [blue]{tags}"
                    ),
                }
                raise ContentDoesNotExist(type="answers", **info)

            if data["isLastBatch"]:
                break

        return tables

    @validate_arguments
    def columns(self, guids: List[GUID], *, include_hidden: bool = False, chunksize: int = 10) -> RecordsFormat:
        """ """
        columns = []

        for chunk in chunks(guids, n=chunksize):
            r = self.ts.api.metadata.details(id=chunk, showhidden=include_hidden)

            for logical_table in r.json()["storables"]:
                for column in logical_table.get("columns", []):
                    columns.append(
                        {
                            "column_guid": column["header"]["id"],
                            "object_guid": logical_table["header"]["id"],
                            "column_name": column["header"]["name"],
                            "description": column["header"].get("description"),
                            "data_type": column["dataType"],
                            "column_type": column["type"],
                            "additive": column["isAdditive"],
                            "aggregation": column["defaultAggrType"],
                            "hidden": column["header"]["isHidden"],
                            "synonyms": column["synonyms"],
                            "index_type": column["indexType"],
                            "geo_config": self._lookup_geo_config(column),
                            "index_priority": column["indexPriority"],
                            "format_pattern": column.get("formatPattern"),
                            "currency_type": self._lookup_currency_type(column),
                            "attribution_dimension": column["isAttributionDimension"],
                            "spotiq_preference": column["spotiqPreference"],
                            "calendar_type": self._lookup_calendar_guid(column),
                            "is_formula": "formulaId" in column,
                        }
                    )

        return columns

    # SUPPORTS .logical_table_columns

    def _lookup_geo_config(self, column_details) -> Optional[str]:
        try:
            config = column_details["geoConfig"]
        except KeyError:
            return None

        if config["type"] in ("LATITUDE", "LONGITUDE"):
            return config["type"].title()
        elif config["type"] == "ZIP_CODE":
            return "Zipcode"
        elif config["type"] == "ADMIN_DIV_0":
            return "Country"
        # things get messy here....
        elif config["type"] in ("ADMIN_DIV_1", "ADMIN_DIV_2"):
            return "Sub-nation Region"

        return "Unknown"

    def _lookup_calendar_guid(self, column_details) -> Optional[str]:
        try:
            ccal_guid = column_details["calendarTableGUID"]
        except KeyError:
            return None

        if ccal_guid not in self.cache["calendar_type"]:
            r = self.ts.api.metadata_list(metadata_type="LOGICAL_TABLE", showhidden=True, fetchids=[ccal_guid])
            d = r.json()["headers"][0]
            self.cache["calendar_type"][ccal_guid] = d["name"]

        return self.cache["calendar_type"][ccal_guid]

    def _lookup_currency_type(self, column_details) -> Optional[str]:
        try:
            currency_info = column_details["currencyTypeInfo"]
        except KeyError:
            return None

        name = None
        if currency_info["setting"] == "FROM_USER_LOCALE":
            name = "Infer From Browser"
        elif currency_info["setting"] == "FROM_ISO_CODE":
            name = f'Specify ISO Code: {currency_info["isoCode"]}'
        elif currency_info["setting"] == "FROM_COLUMN":
            g = currency_info["columnGuid"]

            if g not in self.cache["currency_type"]:
                r = self.ts.api.metadata_list(metadata_type="LOGICAL_COLUMN", showhidden=True, fetchids=[g])
                d = r.json()["headers"][0]
                self.cache["currency_type"][g] = name = f'From a column: {d["name"]}'
            else:
                name = self.cache["currency_type"][g]

        return name
