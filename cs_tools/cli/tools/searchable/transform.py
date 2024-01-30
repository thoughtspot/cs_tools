from __future__ import annotations

import itertools as it
import logging

from cs_tools.types import TableRowsFormat

from . import models

log = logging.getLogger(__name__)


def to_user(data) -> models.User:
    return [models.User.from_api_v1(d).dict() for d in data]


def to_group(data) -> models.Group:
    return [models.Group.from_api_v1(d).dict() for d in data]


def to_group_privilege(data) -> models.Group:
    return [_.dict() for _ in it.chain.from_iterable(models.GroupPrivilege.from_api_v1(d) for d in data)]


def to_principal_association(data) -> models.XREFPrincipal:
    return [_.dict() for _ in it.chain.from_iterable(models.XREFPrincipal.from_api_v1(d) for d in data)]


def to_tag(data) -> models.MetadataObject:
    return [models.Tag.from_api_v1(d).dict() for d in data]


def to_metadata_object(data) -> models.MetadataObject:
    return [models.MetadataObject.from_api_v1(d).dict() for d in data]


def to_metadata_column(data) -> models.MetadataColumn:
    return [models.MetadataColumn.from_api_v1(d).dict() for d in data]


def to_column_synonym(data: TableRowsFormat) -> list[models.ColumnSynonym]:
    """
    Clean and de-duplicate synonyms.

    ThoughtSpot does not perform any validation on duplicate column synonyms.
    """
    seen: set[tuple] = set()
    sanitized: list[models.ColumnSynonym] = []

    for row in data:
        for synonym in row["synonyms"]:
            model = models.ColumnSynonym.validated_init(column_guid=row["column_guid"], synonym=synonym)
            unique = tuple(model.model_dump().values())

            if unique in seen:
                log.info(f"Column {model.column_guid} from {row['object_guid']} has duplicate synonym: {model.synonym}")
                continue

            seen.add(unique)
            sanitized.append(model)

    return [row.model_dump() for row in sanitized]


def to_tagged_object(data) -> models.TaggedObject:
    return [_.dict() for _ in it.chain.from_iterable(models.TaggedObject.from_api_v1(d) for d in data if d["tags"])]


def to_dependent_object(data) -> models.DependentObject:
    return [models.DependentObject.from_api_v1(d).dict() for d in data]


def to_sharing_access(data) -> models.SharingAccess:
    return [models.SharingAccess.from_api_v1(d).dict() for d in data]
