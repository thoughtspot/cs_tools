from typing import Any, Dict, List, Union
import logging

from pydantic import validate_arguments

from cs_tools.data.enums import (
    DownloadableContent, GUID, MetadataCategory, MetadataObject, MetadataObjectSubtype,
)
from cs_tools.errors import ContentDoesNotExist
from cs_tools.util import chunks


log = logging.getLogger(__name__)


class MetadataMiddleware:
    """
    """
    def __init__(self, ts):
        self.ts = ts
        self.cache = {
            'calendar_type': {},
            'currency_type': {},
        }

    @validate_arguments
    def all(
        self,
        *,
        tags: Union[str, List[str]] = None,
        category: MetadataCategory = MetadataCategory.all,
        exclude_system_content: bool = True,
        chunksize: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Get all metadata in ThoughtSpot.

        This includes all liveboards, answer, worksheets, views, and tables.

        Parameters
        ----------
        tags : str, or list of str
          content which are specifically tagged or stickered

        category : str = 'all'
          one of: 'all', 'yours', or 'favorites'

        exclude_system_content : bool = True
          whether or not to include system-generated content

        Returns
        -------
        content : List[Dict[str, Any]]
          all content headers
        """
        if isinstance(tags, str):
            tags = [tags]

        content = []
        types = ['PINBOARD_ANSWER_BOOK', 'QUESTION_ANSWER_BOOK', 'LOGICAL_TABLE']
        track_guids = {}

        for type_ in types:
            offset = 0

            while True:
                r = self.ts.api._metadata.list(
                        type=type_,
                        category=category,
                        tagname=tags,
                        batchsize=chunksize,
                        offset=offset
                    )

                data = r.json()
                to_extend = []

                for d in data['headers']:
                    track_guids[d['id']] = d['name']

                    # inject the type (only objects with subtypes define .type)
                    to_extend.append({'type': type_, **d})

                offset += len(to_extend)

                if exclude_system_content:
                    to_extend = [
                        answer
                        for answer in to_extend
                        if answer.get('authorName') not in ('system', 'tsadmin', 'su')
                    ]

                content.extend(to_extend)

                if data['isLastBatch']:
                    break

        if not content:
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
                )
            }
            raise ContentDoesNotExist(type="content", **info)

        return content

    @validate_arguments
    def columns(
        self,
        guids: List[GUID],
        *,
        include_hidden: bool = False,
        chunksize: int = 10
    ) -> List[Dict[str, Any]]:
        """
        """
        columns = []

        for chunk in chunks(guids, n=chunksize):
            r = self.ts.api.metadata.details(id=chunk, showhidden=include_hidden)

            for logical_table in r.json()['storables']:
                for column in logical_table.get('columns', []):
                    columns.append({
                        'column_guid': column['header']['id'],
                        'object_guid': logical_table['header']['id'],
                        'column_name': column['header']['name'],
                        'description': column['header'].get('description'),
                        'data_type': column['dataType'],
                        'column_type': column['type'],
                        'additive': column['isAdditive'],
                        'aggregation': column['defaultAggrType'],
                        'hidden': column['header']['isHidden'],
                        'synonyms': column['synonyms'],
                        'index_type': column['indexType'],
                        'geo_config': self._lookup_geo_config(column),
                        'index_priority': column['indexPriority'],
                        'format_pattern': column.get('formatPattern'),
                        'currency_type': self._lookup_currency_type(column),
                        'attribution_dimension': column['isAttributionDimension'],
                        'spotiq_preference': column['spotiqPreference'],
                        'calendar_type': self._lookup_calendar_guid(column),
                        'is_formula': 'formulaId' in column,
                    })

        return columns

    @validate_arguments
    def permissions(
        self,
        guids: List[GUID],
        *,
        type: Union[MetadataObject, MetadataObjectSubtype],
        # release in 7.2.0+
        # permission_type: PermissionType = PermissionType.explicit,
        chunksize: int = 15
    ) -> List[Dict[str, Any]]:
        """
        """
        types = {
            'FORMULA': 'LOGICAL_COLUMN',
            'CALENDAR_TABLE': 'LOGICAL_COLUMN',
            'LOGICAL_COLUMN': 'LOGICAL_COLUMN',
            'QUESTION_ANSWER_BOOK': 'QUESTION_ANSWER_BOOK',
            'PINBOARD_ANSWER_BOOK': 'PINBOARD_ANSWER_BOOK',
            'ONE_TO_ONE_LOGICAL': 'LOGICAL_TABLE',
            'USER_DEFINED': 'LOGICAL_TABLE',
            'WORKSHEET': 'LOGICAL_TABLE',
            'AGGR_WORKSHEET': 'LOGICAL_TABLE',
            'MATERIALIZED_VIEW': 'LOGICAL_TABLE',
            'SQL_VIEW': 'LOGICAL_TABLE',
            'LOGICAL_TABLE': 'LOGICAL_TABLE',
        }

        sharing_access = []
        user_guids = [user['id'] for user in self.ts.user.all()]

        for chunk in chunks(guids, n=chunksize):
            r = self.ts.api._security.defined_permission(type=types[type.value], id=chunk)

            for data in r.json().values():
                for shared_to_principal_guid, permission in data['permissions'].items():
                    d = {
                        'object_guid': permission['topLevelObjectId'],
                        # 'shared_to_user_guid':
                        # 'shared_to_group_guid':
                        'permission_type': 'DEFINED',
                        'share_mode': permission['shareMode']
                    }

                    if shared_to_principal_guid in user_guids:
                        d['shared_to_user_guid'] = shared_to_principal_guid
                    else:
                        d['shared_to_group_guid'] = shared_to_principal_guid

                    sharing_access.append(d)

        return sharing_access

    @validate_arguments
    def dependents(
        self,
        guids: List[GUID],
        *,
        for_columns: bool = False,
        include_columns: bool = False,
        chunksize: int = 50
    ) -> List[Dict[str, Any]]:
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
        dependencies : List[Dict[str, Any]]
          all dependencies' headers
        """
        if include_columns:
            guids = [column['header']['id'] for column in self.columns(guids)]
            type_ = 'LOGICAL_COLUMN'
        elif for_columns:
            type_ = 'LOGICAL_COLUMN'
        else:
            type_ = 'LOGICAL_TABLE'

        dependents = []

        for chunk in chunks(guids, n=chunksize):
            r = self.ts.api._dependency.list_dependents(id=chunk, type=type_)
            data = r.json()

            for parent_guid, all_dependencies in data.items():
                for dependency_type, headers in all_dependencies.items():
                    for header in headers:
                        dependents.append({
                            'parent_guid': parent_guid,
                            'type': dependency_type,
                            **header
                        })

        return dependents

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
                    if metadata_type == DownloadableContent.logical_table:
                        mapped_guids.append({"id": metadata["id"], "type": self.map_subtype_to_type(metadata.get("type"))})
                    else:
                        mapped_guids.append({"id": metadata["id"], "type": metadata_type.value})

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
    def map_subtype_to_type(self, subtype: Union[str, None]) -> str:
        """
        Takes a string subtype and maps to a type.  Only LOGICAL_TABLES have sub-types.
        :param subtype: The subtype to map, such as WORKSHEET
        :return: The type for the subtype, such as LOGICAL_TABLE or the subtype.
        """
        if subtype in set(t.value for t in MetadataObjectSubtype):
            return DownloadableContent.logical_table.value

        return subtype

    def _lookup_geo_config(self, column_details) -> Union[str, None]:
        try:
            config = column_details['geoConfig']
        except KeyError:
            return None

        if config['type'] in ('LATITUDE', 'LONGITUDE'):
            return config['type'].title()
        elif config['type'] == 'ZIP_CODE':
            return 'Zipcode'
        elif config['type'] == 'ADMIN_DIV_0':
            return 'Country'
        # things get messy here....
        elif config['type'] in ('ADMIN_DIV_1', 'ADMIN_DIV_2'):
            return 'Sub-nation Region'

        return 'Unknown'

    def _lookup_calendar_guid(self, column_details) -> Union[str, None]:
        try:
            ccal_guid = column_details['calendarTableGUID']
        except KeyError:
            return None

        if ccal_guid not in self.cache['calendar_type']:
            r = self.ts.api._metadata.list(type='LOGICAL_TABLE', showhidden=True, fetchids=[ccal_guid])
            d = r.json()['headers'][0]
            self.cache['calendar_type'][ccal_guid] = d['name']

        return self.cache['calendar_type'][ccal_guid]

    def _lookup_currency_type(self, column_details) -> Union[str, None]:
        try:
            currency_info = column_details['currencyTypeInfo']
        except KeyError:
            return None

        name = None
        if currency_info['setting'] == 'FROM_USER_LOCALE':
            name = 'Infer From Browser'
        elif currency_info['setting'] == 'FROM_ISO_CODE':
            name = f'Specify ISO Code: {currency_info["isoCode"]}'
        elif currency_info['setting'] == 'FROM_COLUMN':
            g = currency_info['columnGuid']

            if g not in self.cache['currency_type']:
                r = self.ts.api._metadata.list(type='LOGICAL_COLUMN', showhidden=True, fetchids=[g])
                d = r.json()['headers'][0]
                self.cache['currency_type'][g] = name = f'From a column: {d["name"]}'
            else:
                name = self.cache['currency_type'][g]

        return name

    @validate_arguments
    def objects_exist(self, metadata_type: MetadataObject, guids: List[GUID]) -> Dict[GUID, bool]:
        """
        Checks if the list of objects exist.
        :param metadata_type: The type to check for.  Must do one at a time.
        :param guids: The list of GUIDs to check.
        :return: A map of GUID to boolean, where True == it exists.
        """
        r = self.ts.api.metadata.list_object_headers(type=metadata_type, fetchids=guids)
        content = r.json()

        # The response is a list of objects that only include the ones that exist.  So check each GUID and add to the
        # map.
        returned_ids = [obj.get("id") for obj in content]
        existence = {}
        for guid in guids:
            existence[guid] = guid in returned_ids

        return existence

    @classmethod
    @validate_arguments
    def tml_type_to_metadata_object(cls, tml_type: str) -> Union[MetadataObject, None]:
        """
        Converts a tml type (e.g. "worksheet") to a MetadataObject type, (e.g. MetadataObject.logical_table)
        :param tml_type:  The TML type, such as None
        """
        mapping = {
            "table": MetadataObject.logical_table,
            "view": MetadataObject.logical_table,
            "worksheet": MetadataObject.logical_table,
            "pinboard": MetadataObject.pinboard,
            "liveboard": MetadataObject.pinboard,
            "answer": MetadataObject.saved_answer,
        }

        return mapping.get(tml_type, None)
