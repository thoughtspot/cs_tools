import itertools as it

from cs_tools.data import models


def to_user(data) -> models.User:
    return [models.User.from_api_v1(d).dict() for d in data]


def to_group(data) -> models.Group:
    return [models.Group.from_api_v1(d).dict() for d in data]


def to_group_privilege(data) -> models.Group:
    return [
        _.dict()
        for _ in it.chain.from_iterable(models.GroupPrivilege.from_api_v1(d) for d in data)
    ]


def to_principal_association(data) -> models.XREFPrincipal:
    return [
        _.dict()
        for _ in it.chain.from_iterable(models.XREFPrincipal.from_api_v1(d) for d in data)
    ]


def to_tag(data) -> models.MetadataObject:
    return [models.Tag.from_api_v1(d).dict() for d in data]


def to_metadata_object(data) -> models.MetadataObject:
    return [models.MetadataObject.from_api_v1(d).dict() for d in data]


def to_metadata_column(data) -> models.MetadataColumn:
    return [models.MetadataColumn.from_api_v1(d).dict() for d in data]


def to_tagged_object(data) -> models.TaggedObject:
    return [
        _.dict()
        for _ in it.chain.from_iterable(models.TaggedObject.from_api_v1(d) for d in data if d['tags'])
    ]


def to_dependent_object(data) -> models.DependentObject:
    return [models.DependentObject.from_api_v1(d).dict() for d in data]


def to_sharing_access(data) -> models.SharingAccess:
    return [models.SharingAccess.from_api_v1(d).dict() for d in data]
