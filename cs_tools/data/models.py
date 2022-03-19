from typing import Any, Dict, List, Optional, Union
import datetime as dt

from sqlmodel import Field, Relationship, SQLModel
from dateutil import tz

from .enums import Privilege


class ThoughtSpotPlatform(SQLModel):
    """
    Information about the ThoughtSpot deployment.
    """
    version: str
    deployment: str
    url: str
    timezone: str
    cluster_name: str
    cluster_id: str

    @property
    def tz(self) -> dt.timezone:
        return tz.gettz(self.timezone)

    @classmethod
    def from_session_info(cls, info: Dict[str, Any]):
        """
        Form a User from the session/info response.
        """
        data = {
            'version': info['releaseVersion'],
            'deployment': 'cloud' if info['configInfo']['isSaas'] else 'software',
            'url': info['configInfo']['emailConfig']['welcomeEmailConfig']['getStartedLink'],
            'timezone': info['timezone'],
            'cluster_name': info['configInfo']['selfClusterName'],
            'cluster_id': info['configInfo']['selfClusterId'],
        }

        return cls(**data)


class LoggedInUser(SQLModel):
    """
    Information about the currently authenticed user.
    """
    guid: str
    name: str
    display_name: str
    email: str
    # Sometimes we get weird NULL privilege in data.. so we'll just accept some others
    privileges: List[Union[Privilege, str, int]]

    @classmethod
    def from_session_info(cls, info: Dict[str, Any]):
        """
        Form a User from the session/info response.
        """
        data = {
            'guid': info['userGUID'],
            'name': info['userName'],
            'display_name': info['userDisplayName'],
            'email': info['userEmail'],
            'privileges': info['privileges']
        }

        return cls(**data)


class User(SQLModel, table=True):
    __tablename__ = 'ts_user'
    user_guid: str = Field(primary_key=True)
    username: str
    email: Optional[str]
    display_name: str
    sharing_visibility: str
    created: dt.datetime
    modified: dt.datetime
    user_type: str

    groups: Optional[List['XREFPrincipal']] = Relationship(back_populates='user')
    content: Optional[List['MetadataObject']] = Relationship(back_populates='author')
    dependent_content: Optional[List['DependentObject']] = Relationship(back_populates='author')
    sharing: Optional[List['SharingAccess']] = Relationship(back_populates='shared_to_user')
    bi_actions: Optional[List['BIServer']] = Relationship(back_populates='user')

    @classmethod
    def from_api_v1(cls, data) -> 'User':
        """
        Takes input from /tspublic/v1/user.
        """
        data = {
            'user_guid': data['header']['id'],
            'username': data['header']['name'],
            'email': data['userContent']['userProperties'].get('mail'),
            'display_name': data['header']['displayName'],
            'sharing_visibility': data['visibility'],
            'created': data['header']['created'],
            'modified': data['header']['modified'],
            'user_type': data['type']
        }
        return cls(**data)


class Group(SQLModel, table=True):
    __tablename__ = 'ts_group'
    group_guid: str = Field(primary_key=True)
    group_name: str
    description: Optional[str]
    display_name: str
    sharing_visibility: str
    created: dt.datetime
    modified: dt.datetime
    group_type: str

    groups: Optional[List['XREFPrincipal']] = Relationship(back_populates='group')
    privileges: List['GroupPrivilege'] = Relationship(back_populates='group')
    sharing: Optional[List['SharingAccess']] = Relationship(back_populates='shared_to_group')

    @classmethod
    def from_api_v1(cls, data) -> 'Group':
        """
        Takes input from /tspublic/v1/group.
        """
        data = {
            'group_guid': data['header']['id'],
            'group_name': data['header']['name'],
            'description': data['header'].get('description'),
            'display_name': data['header']['displayName'],
            'sharing_visibility': data['visibility'],
            'created': data['header']['created'],
            'modified': data['header']['modified'],
            'group_type': data['type']
        }
        return cls(**data)


class GroupPrivilege(SQLModel, table=True):
    __tablename__ = 'ts_group_privilege'
    group_guid: str = Field(primary_key=True, foreign_key='ts_group.group_guid')
    privilege: str = Field(primary_key=True)

    group: 'Group' = Relationship(back_populates='privileges')

    @classmethod
    def from_api_v1(cls, data) -> List['GroupPrivilege']:
        """
        Takes input from /tspublic/v1/user or /tspublic/v1/group.
        """
        return [
            cls(group_guid=data['header']['id'], privilege=p)
            for p in data['privileges']
        ]


class XREFPrincipal(SQLModel, table=True):
    __tablename__ = 'ts_xref_principal'
    principal_guid: str = Field(primary_key=True, foreign_key='ts_user.user_guid')
    group_guid: str = Field(primary_key=True, foreign_key='ts_group.group_guid')

    # TODO: how do we portray nested groups?
    user: 'User' = Relationship(back_populates='groups')
    group: 'Group' = Relationship(back_populates='groups')

    @classmethod
    def from_api_v1(cls, data) -> List['XREFPrincipal']:
        """
        Takes input from /tspublic/v1/user or /tspublic/v1/group.
        """
        return [cls(principal_guid=data['header']['id'], group_guid=g) for g in data['assignedGroups']]


class Tag(SQLModel, table=True):
    __tablename__ = 'ts_tag'
    tag_guid: str = Field(primary_key=True)
    tag_name: str
    color: str
    author_guid: str = Field(foreign_key='ts_user.user_guid')
    created: dt.datetime
    modified: dt.datetime

    tagged_objects: Optional[List['TaggedObject']] = Relationship(back_populates='tag')

    @classmethod
    def from_api_v1(cls, data) -> List['Tag']:
        """
        Takes input from /tspublic/v1/metadata/list.
        """
        return cls(
            tag_guid=data['id'], tag_name=data['id'],
            color=data['clientState']['color'], author_guid=data['author'],
            created=data['created'], modified=data['modified']
        )


class MetadataObject(SQLModel, table=True):
    __tablename__ = 'ts_metadata_object'
    object_guid: str = Field(primary_key=True)
    context: Optional[str]
    name: str
    description: Optional[str]
    author_guid: str = Field(foreign_key='ts_user.user_guid')
    created: dt.datetime
    modified: dt.datetime
    object_type: str

    author: 'User' = Relationship(back_populates='content')
    dependents: Optional[List['DependentObject']] = Relationship(back_populates='parent')
    tagged_objects: Optional[List['TaggedObject']] = Relationship(back_populates='metadata_object')
    sharing: Optional[List['SharingAccess']] = Relationship(back_populates='metadata_object')
    bi_actions: Optional[List['BIServer']] = Relationship(back_populates='metadata_object')

    @classmethod
    def from_api_v1(cls, data) -> 'TaggedObject':
        """
        Takes input from /tspublic/v1/metadata/list.

        Input data is filtered on just the headers for the following types:
            - PINBOARD_ANSWER_BOOK
            - QUESTION_ANSWER_BOOK
            - LOGICAL_TABLE
            - LOGICAL_COLUMN
        """
        data = {
            'object_guid': data['id'],
            'context': data.get('context'),
            'name': data['name'],
            'description': data.get('description'),
            'author_guid': data['author'],
            'created': data['created'],
            'modified': data['modified'],
            'object_type': data['type'],
        }
        return cls(**data)


class TaggedObject(SQLModel, table=True):
    __tablename__ = 'ts_tagged_object'
    object_guid: str = Field(primary_key=True, foreign_key='ts_metadata_object.object_guid')
    tag_guid: str = Field(primary_key=True, foreign_key='ts_tag.tag_guid')

    metadata_object: 'MetadataObject' = Relationship(back_populates='tagged_objects')
    tag: 'Tag' = Relationship(back_populates='tagged_objects')

    @classmethod
    def from_api_v1(cls, data) -> List['TaggedObject']:
        """
        Takes input from /tspublic/v1/metadata/list.
        """
        return [cls(object_guid=data['id'], tag_guid=t['id']) for t in data['tags']]


class DependentObject(SQLModel, table=True):
    __tablename__ = 'ts_dependent_object'
    dependent_guid: str = Field(primary_key=True)
    parent_guid: str = Field(primary_key=True, foreign_key='ts_metadata_object.object_guid')
    name: str
    description: Optional[str]
    author_guid: str = Field(foreign_key='ts_user.user_guid')
    created: dt.datetime
    modified: dt.datetime
    object_type: str

    author: 'User' = Relationship(back_populates='dependent_content')
    parent: 'MetadataObject' = Relationship(back_populates='dependents')

    @classmethod
    def from_api_v1(cls, data) -> 'DependentObject':
        """
        Takes input from /tspublic/v1/dependency/listdependents.

        Input data is augmented with the parent's guid, and the dependent type.
        """
        data = {
            'dependent_guid': data['id'],
            'parent_guid': data['parent_guid'],
            'name': data['name'],
            'description': data.get('description'),
            'author_guid': data['author'],
            'created': data['created'],
            'modified': data['modified'],
            'object_type': data['type'],
        }
        return cls(**data)


class SharingAccess(SQLModel, table=True):
    __tablename__ = 'ts_sharing_access'
    object_guid: str = Field(primary_key=True, foreign_key='ts_metadata_object.object_guid')
    shared_to_user_guid: Optional[str] = Field(primary_key=True, foreign_key='ts_user.user_guid')
    shared_to_group_guid: Optional[str] = Field(primary_key=True, foreign_key='ts_group.group_guid')
    permission_type: str = Field(primary_key=True)
    share_mode: str

    metadata_object: 'MetadataObject' = Relationship(back_populates='sharing')
    shared_to_user: 'User' = Relationship(back_populates='sharing')
    shared_to_group: 'Group' = Relationship(back_populates='sharing')


class BIServer(SQLModel, table=True):
    __tablename__ = 'ts_bi_server'
    incident_id: str = Field(primary_key=True)
    timestamp: dt.datetime
    url: str
    http_response_code: str
    browser_type: str
    browser_version: str
    client_type: str
    client_id: str
    answer_book_guid: str = Field(foreign_key='ts_metadata_object.object_guid')
    viz_id: str
    user_id: str = Field(foreign_key='ts_user.user_guid')
    user_action: str
    query_text: str
    response_size: int
    latency_us: int
    impressions: int

    metadata_object: 'MetadataObject' = Relationship(back_populates='bi_actions')
    user: 'User' = Relationship(back_populates='bi_actions')
