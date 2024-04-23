from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import logging

from cs_tools import utils
from cs_tools.errors import CSToolsError
from cs_tools.types import (
    GUID,
    MetadataObjectType,
    MetadataParent,
    PermissionType,
    TableRowsFormat,
    TMLSupportedContent,
)

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


class MetadataMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts
        self._details_cache: dict[GUID, dict] = {}

    def permissions(
        self,
        guids: list[GUID],
        *,
        metadata_type: MetadataObjectType,
        permission_type: PermissionType = PermissionType.explicit,
        chunksize: int = 25,
    ) -> TableRowsFormat:
        """
        Fetch permissions for a given object type.
        """
        sharing_access = []
        group_guids = [group["id"] for group in self.ts.group.all()]

        for chunk in utils.batched(guids, n=chunksize):
            r = self.ts.api.v1.security_metadata_permissions(metadata_type=metadata_type, guids=chunk)

            for data in r.json().values():
                for shared_to_principal_guid, permission in data["permissions"].items():
                    d = {
                        "object_guid": permission["topLevelObjectId"],
                        # 'shared_to_user_guid':
                        # 'shared_to_group_guid':
                        "permission_type": permission_type,
                        "share_mode": permission["shareMode"],
                    }

                    if shared_to_principal_guid in group_guids:
                        d["shared_to_group_guid"] = shared_to_principal_guid
                    else:
                        d["shared_to_user_guid"] = shared_to_principal_guid

                    sharing_access.append(d)

        return sharing_access

    def dependents(
        self, guids: list[GUID], *, for_columns: bool = False, include_columns: bool = False, chunksize: int = 50
    ) -> TableRowsFormat:
        """
        Get all dependencies of content in ThoughtSpot.

        Only worksheets, views, and tables may have content built on top of
        them, and passing Answer or Liveboard GUIDs will render no results.

        Parameters
        ----------
        guids : list of GUIDs
          content to find dependencies for

        for_columns : bool, default False
          whether or not the guids passed are of columns themselves

        include_columns : bool, default False
          whether or not to find guids of the columns in a piece of content

        Returns
        -------
        dependencies : TableRowsFormat
          all dependencies' headers
        """
        if include_columns:
            guids = [column["header"]["id"] for column in self.ts.logical_table.columns(guids)]
            type_ = "LOGICAL_COLUMN"
        elif for_columns:
            type_ = "LOGICAL_COLUMN"
        else:
            type_ = "LOGICAL_TABLE"

        dependents = []

        for chunk in utils.batched(guids, n=chunksize):
            r = self.ts.api.v1.dependency_list_dependents(guids=chunk, metadata_type=type_)
            data = r.json()

            for parent_guid, all_dependencies in data.items():
                for dependency_type, headers in all_dependencies.items():
                    for header in headers:
                        dependents.append({"parent_guid": parent_guid, "metadata_type": dependency_type, **header})

        return dependents

    def get(self, guids: list[GUID]) -> TableRowsFormat:
        """
        Find all objects based on the supplied guids.
        """
        content: list[TableRowsFormat] = []
        guids = set(guids)

        for metadata_type in MetadataObjectType:
            r = self.ts.api.v1.metadata_list(metadata_type=metadata_type, fetch_guids=list(guids))

            for header in r.json()["headers"]:
                header["metadata_type"] = metadata_type
                header["type"] = header.get("type", None)

                if header["id"] in guids:
                    content.append(header)
                    guids.discard(header["id"])

            if not guids:
                break

        if guids:
            raise CSToolsError(
                title=f"failed to find content for guids: {guids}",
                reason="GUIDs not found in ThoughtSpot",
                suggestion="check the GUIDs passed to the function and verify they exist.",
            )

        return content

    def find(
        self,
        *,
        tags: Optional[list[str]] = None,
        author: GUID = None,
        pattern: Optional[str] = None,
        include_types: Optional[list[str]] = None,
        include_subtypes: Optional[list[str]] = None,
        exclude_types: Optional[list[str]] = None,
        exclude_subtypes: Optional[list[str]] = None,
    ) -> TableRowsFormat:
        """
        Find all object which meet the predicates in the keyword args.
        """
        content = []
        metadata_list_kw = {}

        if tags is not None:
            metadata_list_kw["tag_names"] = tags

        if author is not None:
            metadata_list_kw["author_guid"] = self.ts.user.guid_for(author)

        if pattern is not None:
            metadata_list_kw["pattern"] = pattern

        for metadata_type in MetadataObjectType:
            # can't exclude logical tables because they have sub-types.  Logical tables will be checked on subtype.
            if (
                exclude_types
                and metadata_type is not MetadataObjectType.logical_table
                and (metadata_type in exclude_types)
            ):
                continue

            if include_types and (metadata_type not in include_types):
                continue

            metadata_list_kw["offset"] = 0

            while True:
                r = self.ts.api.v1.metadata_list(metadata_type=metadata_type, batchsize=500, **metadata_list_kw)

                if r.is_error:
                    metadata_list_kw["metadata_type"] = metadata_type
                    log.error(f"The following metadata/list parameters caused an error\n{metadata_list_kw}")
                    break

                data = r.json()
                metadata_list_kw["offset"] += len(data["headers"])

                for header in data["headers"]:
                    subtype = header.get("type", None)

                    # All subtypes will be retrieved, so need to filter the subtype appropriately.
                    # Mainly applies to LOGICAL_TABLE.
                    if include_subtypes and subtype and (subtype not in include_subtypes):
                        continue
                    elif exclude_subtypes and subtype and (subtype in exclude_subtypes):
                        continue

                    header["metadata_type"] = metadata_type
                    header["type"] = subtype
                    content.append(header)

                if data["isLastBatch"]:
                    break

        return content

    def objects_exist(self, metadata_type: MetadataObjectType, guids: list[GUID]) -> dict[GUID, bool]:
        """
        Check if the input GUIDs exist.
        """
        r = self.ts.api.v1.metadata_list(metadata_type=metadata_type, fetch_guids=guids)

        # metadata/list only returns objects that exist
        existence = {header["id"] for header in r.json()["headers"]}
        return {guid: guid in existence for guid in guids}

    def fetch_header_and_extras(self, metadata_type: MetadataObjectType, guids: list[GUID]) -> list[dict]:
        """
        METADATA DETAILS is expensive. Here's our shortcut.
        """
        data = []

        for guid in guids:
            try:
                data.append(self._details_cache[guid])
                continue
            except KeyError:
                pass

            r = self.ts.api.v1.metadata_details(metadata_type=metadata_type, guids=[guid], show_hidden=True)

            if r.is_error:
                log.warning(f"Failed to fetch details for {guid} ({metadata_type})")
                continue

            d = r.json()["storables"][0]

            header_and_extras = {
                "metadata_type": metadata_type,
                "header": d["header"],
                "type": d.get("type"),  # READ: .subtype  (eg. ONE_TO_ONE_LOGICAL, WORKSHEET, etc..)
                # LOGICAL_TABLE extras
                "dataSourceId": d.get("dataSourceId"),
                "columns": d.get("columns"),
                # VIZ extras (answer, liveboard)
                "reportContent": d.get("reportContent"),
            }

            self._details_cache[guid] = header_and_extras
            data.append(header_and_extras)

        return data

    def find_data_source_of_logical_table(self, guid: GUID) -> GUID:
        """
        METADATA DETAILS is expensive. Here's our shortcut.
        """
        info = self.fetch_header_and_extras(metadata_type="LOGICAL_TABLE", guids=[guid])
        return info[0]["dataSourceId"]

    def table_references(self, guid: GUID, *, tml_type: str, hidden: bool = False) -> list[MetadataParent]:
        """
        Returns a mapping of parent LOGICAL_TABLEs

        The mapping is by guid -> name, where the logical table has been extracted from..

            Worksheet -----> composing LOGICAL_TABLEs, can be any LOGICAL_TABLE
            View ----------> composing LOGICAL_TABLEs, can be any LOGICAL_TABLE
            System Table --> this will have no parents
            SQL View ------> this will have no parents
            Answer --------> the TABLE_VIZ's columns' owner, can be any LOGICAL_TABLE
            Liveboard -----> the hidden Answer's mapping LOGICAL_TABLEs

        """
        metadata_type = TMLSupportedContent.from_friendly_type(tml_type)
        info = self.fetch_header_and_extras(metadata_type=metadata_type, guids=[guid])
        mappings: list[MetadataParent] = []

        # LOOP THROUGH ALL COLUMNS LOOKING FOR TABLES WE HAVEN'T SEEN
        if metadata_type == "LOGICAL_TABLE":
            for column in info[0]["columns"]:
                for logical_table in column["sources"]:
                    parent = MetadataParent(
                        parent_guid=logical_table["tableId"],
                        parent_name=logical_table["tableName"],
                        connection=info[0]["dataSourceId"],
                    )

                    if parent not in mappings:
                        mappings.append(parent)

        # FIND THE TABLE, LOOP THROUGH ALL COLUMNS LOOKING FOR TABLES WE HAVEN'T SEEN
        if metadata_type == "QUESTION_ANSWER_BOOK":
            visualizations = info[0]["reportContent"]["sheets"][0]["sheetContent"]["visualizations"]
            table_viz = next(v for v in visualizations if v["vizContent"]["vizType"] == "TABLE")

            for column in table_viz["vizContent"]["columns"]:
                for logical_table in column["referencedTableHeaders"]:
                    connection_guid = self.find_data_source_of_logical_table(logical_table["id"])

                    parent = MetadataParent(
                        parent_guid=logical_table["id"],
                        parent_name=logical_table["name"],
                        connection=connection_guid,
                    )

                    if parent not in mappings:
                        mappings.append(parent)

        # LOOP THROUGH ALL THE VISUALIZATIONS, FIND THE REFERENCE ANSWER, SEARCH AND ADD THE ANSWER-VIZ MAPPINGS
        if metadata_type == "PINBOARD_ANSWER_BOOK":
            visualizations = info[0]["reportContent"]["sheets"][0]["sheetContent"]["visualizations"]

            for idx, visualization in enumerate(visualizations, start=1):
                viz_mappings = self.table_references(
                    visualization["vizContent"]["refAnswerBook"]["id"],
                    tml_type="answer",
                    hidden=True,
                )

                for parent in viz_mappings:
                    parent.visualization_guid = visualization["header"]["id"]
                    parent.visualization_index = f"Viz_{idx}"

                    if parent not in mappings:
                        mappings.append(parent)

        return mappings
