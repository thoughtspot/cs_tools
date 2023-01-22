from __future__ import annotations
from typing import List, Tuple
import collections

from cs_tools.thoughtspot import ThoughtSpot
from cs_tools._compat import TypedDict
from cs_tools.types import SecurityPrincipal


class _UserInfo(TypedDict):
    username: str
    email: str
    display_name: str
    visibility: str  # one of: DEFAULT, NOT_SHAREABLE
    type: str  # principal


class _GroupInfo(TypedDict):
    username: str
    email: str
    display_name: str
    visibility: str  # one of: DEFAULT, NOT_SHAREABLE
    type: str  # principal


class _AssociationInfo(TypedDict):
    principal_name: str
    principal_type: str
    group_name: str


def _get_current_security(ts: ThoughtSpot) -> Tuple[List[_UserInfo], List[_GroupInfo], List[_AssociationInfo]]:
    """ """
    users_and_groups: List[SecurityPrincipal] = ts.api.user_list().json()
    users: List[_UserInfo] = []
    groups: List[_GroupInfo] = []
    associations: List[_AssociationInfo] = []

    for principal in users_and_groups:
        data = {
            "display_name": principal["displayName"],
            "visibility": principal["visibility"],
            "type": principal["principalTypeEnum"],
        }

        if "USER" in principal["principalTypeEnum"]:
            type_ = "USER"
            users.append({"username": principal["name"], "email": principal["mail"], **data})

        if "GROUP" in principal["principalTypeEnum"]:
            type_ = "GROUP"
            groups.append({"group_name": principal["name"], "description": principal.get("description"), **data})

        for group in principal["groupNames"]:
            associations.append({"principal_name": principal["name"], "principal_type": type_, "group_name": group})

    return users, groups, associations


def _form_principals(
    users: List[_UserInfo],
    groups: List[_GroupInfo],
    xref: List[_AssociationInfo]
) -> List[SecurityPrincipal]:
    principals = []
    principals_groups = collections.defaultdict(list)

    for x in xref:
        principals_groups[x["principal_name"]].append(x["group_name"])

    for group in groups:
        principals.append(
            {
                "name": group["group_name"],
                "displayName": group["display_name"],
                "description": group["description"],
                "principalTypeEnum": group["type"],
                "groupNames": principals_groups[group["group_name"]],
                "visibility": group["visibility"],
            }
        )

    for user in users:
        principals.append(
            {
                "name": user["username"],
                "displayName": user["display_name"],
                "mail": user["email"],
                "principalTypeEnum": user["type"],
                "groupNames": principals_groups[user["username"]],
                "visibility": user["visibility"],
            }
        )

    return principals
