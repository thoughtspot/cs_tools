from __future__ import annotations

import logging

from sqlalchemy import event
from sqlalchemy.types import String, TypeDecorator
import sqlalchemy as sa

log = logging.getLogger(__name__)

# https://docs.aws.amazon.com/redshift/latest/dg/r_Character_types.html#r_Character_types-varchar-or-character-varying
MAX_VARCHAR_LENGTH = 65535


class TrimmedString(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        """Customize how the value is processed before being sent to the database."""
        if value is None:
            pass

        elif len(value) > MAX_VARCHAR_LENGTH:
            log.warning(f"Incoming data value Redshift maxsize: {len(value)} chars, see logs for full value..")
            log.debug(value)
            # MAX_LENGTH minus 4 because..
            # - python is zero indexed
            # - we want to leave 3 characters for the truncation indicator
            #
            value = value[: MAX_VARCHAR_LENGTH - 4] + "..."

        return value


@event.listens_for(sa.MetaData, "before_create")
def before_create(metadata, connection, **kw):
    """Customize how the Table is configured before CREATE TABLE ran in Redshift."""
    for table in metadata.tables.values():
        for column in table.columns:
            try:
                column.info["length_override"]
            except KeyError:
                continue

            log.debug(f"Explicitly setting size of {column.name} to VARCHAR({MAX_VARCHAR_LENGTH})")
            column.type = TrimmedString(length=MAX_VARCHAR_LENGTH)
