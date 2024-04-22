from __future__ import annotations

from typing import Any, Optional
import logging

from sqlalchemy.schema import Column
from sqlalchemy.types import Text
from sqlmodel import Field
import pydantic

from cs_tools.datastructures import ValidatedSQLModel

log = logging.getLogger(__name__)


class AuthUser(ValidatedSQLModel, table=True):
    __tablename__ = "ts_auth_sync_users"
    username: str = Field(primary_key=True)
    email: Optional[str]
    display_name: str
    sharing_visibility: str
    user_type: str


class AuthGroup(ValidatedSQLModel, table=True):
    __tablename__ = "ts_auth_sync_groups"
    group_name: str = Field(primary_key=True)
    description: Optional[str] = Field(sa_column=Column(Text, info={"length_override": "MAX"}))
    display_name: str
    sharing_visibility: str
    group_type: str

    @pydantic.field_validator("description", mode="before")
    @classmethod
    def remove_leading_trailing_spaces(cls, value: Any) -> str:
        return None if value is None else value.strip()


class AuthGroupMembership(ValidatedSQLModel, table=True):
    __tablename__ = "ts_auth_sync_xref"
    principal_name: str = Field(primary_key=True)
    principal_type: str = Field(primary_key=True)
    group_name: str = Field(primary_key=True)


USER_MODELS = [AuthUser, AuthGroup, AuthGroupMembership]
