from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union
import logging

from cs_tools.api import _utils
from cs_tools.errors import ContentDoesNotExist
from cs_tools.types import GUID, MetadataCategory, TableRowsFormat
from cs_tools.utils import chunks

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


class LogicalTableMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts
        self.cache = {"calendar_type": {}, "currency_type": {}}

    def all(  # noqa: A003
        self,
        *,
        tags: Optional[Union[str, list[str]]] = None,
        category: MetadataCategory = MetadataCategory.all,
        hidden: bool = False,
        exclude_system_content: bool = True,
        include_data_source: bool = True,
        chunksize: int = 500,
        raise_on_error: bool = True,
    ) -> TableRowsFormat:
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

        if tags is None:
            tags = []

        tables = []

        while True:
            r = self.ts.api.v1.metadata_list(
                metadata_type="LOGICAL_TABLE",
                category=category,
                tag_names=tags or _utils.UNDEFINED,
                show_hidden=hidden,
                batchsize=chunksize,
                offset=len(tables),
            )

            data = r.json()
            to_extend = data["headers"]

            if exclude_system_content:
                to_extend = [table for table in to_extend if table.get("authorName") not in _utils.SYSTEM_USERS]

            tables.extend([{"metadata_type": "LOGICAL_TABLE", **table} for table in to_extend])

            if not tables and raise_on_error:
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

        if include_data_source:
            for table in tables:
                if table["type"] in ("ONE_TO_ONE_LOGICAL", "SQL_VIEW"):
                    connection_guid = self.ts.metadata.find_data_source_of_logical_table(guid=table["id"])
                    source_details = self.ts.metadata.fetch_data_source_info(guid=connection_guid)
                    table["data_source"] = source_details["header"]
                    table["data_source"]["type"] = source_details["type"]

        return tables

    def columns(self, guids: list[GUID], *, include_hidden: bool = False, chunksize: int = 10) -> TableRowsFormat:
        """ """
        columns = []

        for chunk in chunks(guids, n=chunksize):
            r = self.ts.api.v1.metadata_details(guids=chunk, show_hidden=include_hidden)

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
                        },
                    )

        return columns

    # ==================================================================================================================
    # SUPPORTS .logical_table_columns
    # ==================================================================================================================

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
            r = self.ts.api.v1.metadata_list(metadata_type="LOGICAL_TABLE", show_hidden=True, fetch_guids=[ccal_guid])
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
                r = self.ts.api.v1.metadata_list(metadata_type="LOGICAL_COLUMN", show_hidden=True, fetch_guids=[g])
                d = r.json()["headers"][0]
                self.cache["currency_type"][g] = name = f'From a column: {d["name"]}'
            else:
                name = self.cache["currency_type"][g]

        return name
