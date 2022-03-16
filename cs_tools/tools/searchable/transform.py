import itertools as it

from cs_tools import db_models as model


def to_user(data) -> model.User:
    return [model.User.from_api_v1(d).dict() for d in data]


def to_group(data) -> model.Group:
    return [model.Group.from_api_v1(d).dict() for d in data]


def to_group_privilege(data) -> model.Group:
    return [
        _.dict()
        for _ in it.chain.from_iterable(model.GroupPrivilege.from_api_v1(d) for d in data)
    ]


def to_principal_association(data) -> model.XREFPrincipal:
    return [
        _.dict()
        for _ in it.chain.from_iterable(model.XREFPrincipal.from_api_v1(d) for d in data)
    ]


def to_tag(data) -> model.MetadataObject:
    return [model.Tag.from_api_v1(d).dict() for d in data]


def to_metadata_object(data) -> model.MetadataObject:
    return [model.MetadataObject.from_api_v1(d).dict() for d in data]


def to_tagged_object(data) -> model.TaggedObject:
    return [
        _.dict()
        for _ in it.chain.from_iterable(model.TaggedObject.from_api_v1(d) for d in data if d['tags'])
    ]


def to_dependent_object(data) -> model.DependentObject:
    return [model.DependentObject.from_api_v1(d).dict() for d in data]


def to_sharing_access(data) -> model.SharingAccess:
    return [model.SharingAccess(**d).dict() for d in data]
