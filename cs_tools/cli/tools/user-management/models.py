from __future__ import annotations

import logging
import uuid

from sqlalchemy.schema import Column
from sqlalchemy.types import Text
from sqlmodel import Field

from cs_tools.datastructures import ValidatedSQLModel

log = logging.getLogger(__name__)


class PrincipalMetadataPermission(ValidatedSQLModel, table=True):
    __tablename__ = "ts_transfer_metadata_permission"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    principal_id: str = Field(primary_key=True)
    principal_name: str = Field(sa_column=Column(Text, info={"length_override": "MAX"}))
    metadata_type: str = Field(primary_key=True)
    metadata_id: str = Field(primary_key=True)
    metadata_name: str = Field(sa_column=Column(Text, info={"length_override": "MAX"}))
    permission: str = Field(primary_key=True)
