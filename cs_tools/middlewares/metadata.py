from typing import Any, Dict, List, Union
import logging

from pydantic import validate_arguments

from cs_tools._enums import (
    GUID,
    DownloadableContent,
    LogicalTableSubtype,
)

log = logging.getLogger(__name__)


class MetadataMiddleware:
    """
    TODO - add docs
    """

    def __init__(self, ts):
        self.ts = ts

    @validate_arguments
    def get_edoc_object_list(self, guids: List[GUID]) -> List[Dict[str,str]]:
        """
        Returns a list of objects that map from id to type for edoc calls.

        The return format looks like:
        [
            {"id": "0291f1cd-5f8e-4d96-80e2-e5ef1aa6c44f", "type":"QUESTION_ANSWER_BOOK"},
            {"id": "4bcaadb4-031a-4afd-b159-2c0c0f194c42", "type":"PINBOARD_ANSWER_BOOK"}
        ]
        :param guids: A list of guids to get the types for.
        """

        if not guids:
            return []

        mapped_guids = []

        for metadata_type in DownloadableContent:
            offset = 0

            while True:
                r = self.ts.api._metadata.list(type=metadata_type.value, batchsize=500, offset=offset, fetchids=guids)
                data = r.json()
                offset += len(data)

                for metadata in data['headers']:
                    mapped_guids.append({"id": metadata["id"], "type": self.map_subtype_to_type(metadata.get("type"))})

                if data['isLastBatch']:
                    break

            r = self.ts.api._metadata.list(fetchids=guids)

        return mapped_guids

    @validate_arguments
    def get_object_ids_with_tags(self, tags: List[str]) -> List[Dict[str,str]]:
        """
        Gets a list of IDs for the associated tag and returns as a list of object ID to type mapping.

        The return format looks like:
        [
            {"id": "0291f1cd-5f8e-4d96-80e2-e5ef1aa6c44f", "type":"QUESTION_ANSWER_BOOK"},
            {"id": "4bcaadb4-031a-4afd-b159-2c0c0f194c42", "type":"PINBOARD_ANSWER_BOOK"}
        ]
        :param tags: The list of tags to get ids for.
        """

        object_ids = []
        for metadata_type in DownloadableContent:
            offset = 0

            while True:
                r = self.ts.api._metadata.list(type=metadata_type.value, batchsize=500, offset=offset, tagname=tags)
                data = r.json()
                offset += len(data)

                for metadata in data['headers']:
                    object_ids.append(metadata["id"])

                if data['isLastBatch']:
                    break

        return list(set(object_ids))  # might have been duplicates

    @classmethod
    @validate_arguments
    def map_subtype_to_type(self, subtype: str) -> str:
        """
        Takes a string subtype and maps to a type.  Only LOGICAL_TABLES have sub-types.
        :param subtype: The subtype to map, such as WORKSHEET
        :return: The type for the subtype, such as LOGICAL_TABLE or the subtype.
        """
        if subtype in set(t.value for t in LogicalTableSubtype):
            return DownloadableContent.logical_table.value

        return subtype
