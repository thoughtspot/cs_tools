from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Optional
import datetime as dt

import pydantic

from cs_tools import _types, validators


class User(pydantic.BaseModel):
    cluster_guid: _types.GUID
    user_guid: _types.GUID
    username: _types.Name
    email: Optional[str]
    display_name: str
    sharing_visibility: _types.SharingVisibility
    created: dt.datetime
    modified: dt.datetime
    user_type: str
    org_memberships: set[int] = pydantic.Field(default_factory=set)
    group_memberships: set[_types.Name] = pydantic.Field(default_factory=set)

    @pydantic.field_validator("email")
    @classmethod
    def clean_email(cls, value: Optional[str]) -> Optional[str]:
        return value if value else None

    @pydantic.field_validator("created", "modified", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)

    @classmethod
    def from_syncer_info(
        cls, user_info: _types.APIResult, *, org: _types.OrgIdentifier, info: _types.APIResult
    ) -> User:
        """ """
        groups = {g["group_guid"]: g["group_name"] for g in info["ts_group"] if int(g["org_id"]) == org}

        if memberships := info["ts_xref_org"]:
            user_info["org_memberships"] = {
                m["org_id"] for m in memberships if user_info["user_guid"] == m["user_guid"]
            }

        if memberships := info["ts_xref_principal"]:
            user_info["group_memberships"] = {
                groups[m["group_guid"]]
                for m in memberships
                if user_info["user_guid"] == m["principal_guid"]
                if m["group_guid"] in groups
            }

        me = cls.model_validate(user_info)

        return me

    def __hash__(self) -> int:
        fields = (
            self.cluster_guid,
            self.user_guid,
            self.username,
            self.email,
            self.display_name,
            self.sharing_visibility,
            tuple(sorted(self.org_memberships)),
            tuple(sorted(self.group_memberships)),
        )
        return hash(fields)

    def __eq__(self, other) -> bool:
        return hash(self) == hash(other)


class Group(pydantic.BaseModel):
    cluster_guid: _types.GUID
    org_id: int
    group_guid: _types.GUID
    group_name: _types.Name
    description: Optional[str]
    display_name: str
    sharing_visibility: _types.SharingVisibility
    created: dt.datetime
    modified: dt.datetime
    group_type: str
    privileges: set[_types.GroupPrivilege]
    group_memberships: set[_types.Name]

    @pydantic.field_validator("created", "modified", mode="before")
    @classmethod
    def check_valid_utc_datetime(cls, value: Any) -> dt.datetime:
        return validators.ensure_datetime_is_utc.func(value)

    @classmethod
    def from_syncer_info(cls, guid, *, info) -> Group: ...


def determine_changes(
    existing: Iterable[User], incoming: Iterable[User], key: str
) -> tuple[set[_types.GUID], set[_types.GUID], set[_types.GUID]]:
    """"""
    existing_lookup = {getattr(u, key): u for u in existing}
    incoming_lookup = {getattr(u, key): u for u in incoming}

    existing_guids = set(existing_lookup.keys())
    incoming_guids = set(incoming_lookup.keys())

    created = incoming_guids - existing_guids
    deleted = existing_guids - incoming_guids
    updated = {u for u in (existing_guids & incoming_guids) if existing_lookup[u] != incoming_lookup[u]}

    return created, updated, deleted
