from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Union
import logging

from pydantic import validate_arguments

from cs_tools.errors import CSToolsError
from cs_tools.types import (
    MetadataObjectSubtype,
    TMLSupportedContent,
    MetadataObjectType,
    PermissionType,
    RecordsFormat,
    GUID,
)
from cs_tools import utils

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


class MetadataMiddleware:
    """ """

    def __init__(self, ts: ThoughtSpot):
        self.ts = ts

    @validate_arguments
    def permissions(
        self,
        guids: List[GUID],
        *,
        type: Union[MetadataObjectType, MetadataObjectSubtype],
        permission_type: PermissionType = PermissionType.explicit,
        chunksize: int = 15,
    ) -> RecordsFormat:
        """ """
        type_to_supertype = {
            "FORMULA": "LOGICAL_COLUMN",
            "CALENDAR_TABLE": "LOGICAL_COLUMN",
            "LOGICAL_COLUMN": "LOGICAL_COLUMN",
            "QUESTION_ANSWER_BOOK": "QUESTION_ANSWER_BOOK",
            "PINBOARD_ANSWER_BOOK": "PINBOARD_ANSWER_BOOK",
            "ONE_TO_ONE_LOGICAL": "LOGICAL_TABLE",
            "USER_DEFINED": "LOGICAL_TABLE",
            "WORKSHEET": "LOGICAL_TABLE",
            "AGGR_WORKSHEET": "LOGICAL_TABLE",
            "MATERIALIZED_VIEW": "LOGICAL_TABLE",
            "SQL_VIEW": "LOGICAL_TABLE",
            "LOGICAL_TABLE": "LOGICAL_TABLE",
        }

        sharing_access = []
        user_guids = [user["id"] for user in self.ts.user.all()]

        for chunk in utils.chunks(guids, n=chunksize):
            r = self.ts.api.security_metadata_permissions(metadata_type=type_to_supertype[type.value], guids=chunk)

            for data in r.json().values():
                for shared_to_principal_guid, permission in data["permissions"].items():
                    d = {
                        "object_guid": permission["topLevelObjectId"],
                        # 'shared_to_user_guid':
                        # 'shared_to_group_guid':
                        "permission_type": permission_type.value,
                        "share_mode": permission["shareMode"],
                    }

                    if shared_to_principal_guid in user_guids:
                        d["shared_to_user_guid"] = shared_to_principal_guid
                    else:
                        d["shared_to_group_guid"] = shared_to_principal_guid

                    sharing_access.append(d)

        return sharing_access

    @validate_arguments
    def dependents(
        self, guids: List[GUID], *, for_columns: bool = False, include_columns: bool = False, chunksize: int = 50
    ) -> RecordsFormat:
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
        dependencies : RecordsFormat
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

        for chunk in utils.chunks(guids, n=chunksize):
            r = self.ts.api.dependency_list_dependents(guids=chunk, metadata_type=type_)
            data = r.json()

            for parent_guid, all_dependencies in data.items():
                for dependency_type, headers in all_dependencies.items():
                    for header in headers:
                        dependents.append({"parent_guid": parent_guid, "type": dependency_type, **header})

        return dependents

    @validate_arguments
    def get(self, guids: List[GUID]) -> RecordsFormat:
        """
        Find all objects based on the supplied guids.
        """
        content: List[RecordsFormat] = []
        guids = set(guids)

        for metadata_type in MetadataObjectType:
            r = self.ts.api.metadata_list(metadata_type=metadata_type, fetch_guids=list(guids))

            for header in r.json()["headers"]:
                header["metadata_type"] = metadata_type
                header["type"] = header.get("type", None)

                if header["id"] in guids:
                    content.append(header)
                    guids.discard(header["id"])

            if not guids:
                break

        if guids:
            raise CSToolsError(f"failed to find content for guids: {guids}")

        return content

    @validate_arguments
    def find(
        self,
        *,
        tags: List[str] = None,
        author: GUID = None,
        pattern: str = None,
        include_types: List[str] = None,
        exclude_types: List[str] = None,
        include_subtypes: List[str] = None,
    ) -> RecordsFormat:
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
            if exclude_types is not None and (metadata_type in exclude_types):
                continue

            if include_types is not None and (metadata_type not in include_types):
                continue

            metadata_list_kw["offset"] = 0

            while True:
                r = self.ts.api.metadata_list(metadata_type=metadata_type, batchsize=500, **metadata_list_kw)
                data = r.json()
                metadata_list_kw["offset"] += len(data["headers"])

                for header in data["headers"]:
                    subtype = header.get("type", None)

                    if (include_subtypes is not None) and (subtype is not None) and (subtype not in include_subtypes):
                        continue

                    header["metadata_type"] = metadata_type
                    header["type"] = subtype
                    content.append(header)

                if data["isLastBatch"]:
                    break

        return content

    @validate_arguments
    def objects_exist(self, metadata_type: MetadataObjectType, guids: List[GUID]) -> Dict[GUID, bool]:
        """
        Check if the input GUIDs exist.
        """
        r = self.ts.api.metadata_list(metadata_type=metadata_type, fetch_guids=guids)

        # metadata/list only returns objects that exist
        existence = {header["id"] for header in r.json()["headers"]}
        return {guid: guid in existence for guid in guids}

    @validate_arguments
    def table_references(self, guid: GUID, *, tml_type: str, hidden: bool = False) -> Dict[GUID, str]:
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
        # DEV NOTE: @boonhapus, 2023/01/14
        #   we might need a complex data structure.. i believe that any of these types
        #   can be composed of dissimilar parents with the same name. eg, a Worksheet
        #   with a View and System Table identically named.
        #
        #   Technically, we can resolve this still, as the metadata/details and
        #   metadata/tml/export LOGICAL_TABLE order will be identically sorted.. but TBD
        #
        metadata_type = TMLSupportedContent.from_friendly_type(tml_type)
        r = self.ts.api.metadata_details(guids=[guid], metadata_type=metadata_type, show_hidden=hidden)
        mappings: Dict[GUID, str] = {}  # LOGICAL_TABLE.guid : LOGICAL_TABLE.name

        if "storables" not in r.json():
            log.warning(f"no detail found for {tml_type} = {guid}")
            return mappings

        for storable in r.json()["storables"]:
            # LOOP THROUGH ALL COLUMNS LOOKING FOR TABLES WE HAVEN'T SEEN
            if metadata_type == "LOGICAL_TABLE":
                for column in storable["columns"]:
                    for logical_table in column["sources"]:
                        mappings[logical_table["tableId"]] = logical_table["tableName"]

            # FIND THE TABLE, LOOP THROUGH ALL COLUMNS LOOKING FOR TABLES WE HAVEN'T SEEN
            if metadata_type == "QUESTION_ANSWER_BOOK":
                visualizations = storable["reportContent"]["sheets"][0]["sheetContent"]["visualizations"]
                table_viz = next(v for v in visualizations if v["vizContent"]["vizType"] == "TABLE")

                for column in table_viz["vizContent"]["columns"]:
                    for logical_table in column["referencedTableHeaders"]:
                        mappings[logical_table["id"]] = logical_table["name"]

            # LOOP THROUGH ALL THE VISUALIZATIONS, FIND THE REFERENCE ANSWER, SEARCH AND ADD THE ANSWER-VIZ MAPPINGS
            if metadata_type == "PINBOARD_ANSWER_BOOK":
                visualizations = storable["reportContent"]["sheets"][0]["sheetContent"]["visualizations"]

                for idx, visualization in enumerate(visualizations, start=1):
                    viz_mappings = self.table_references(
                        visualization["vizContent"]["refAnswerBook"]["id"], metadata_type="answer", hidden=True
                    )

                    mappings.update(viz_mappings)

        return mappings
