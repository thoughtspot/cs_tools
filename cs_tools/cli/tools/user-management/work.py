from __future__ import annotations

from typing import TYPE_CHECKING
import collections

from cs_tools._compat import TypedDict

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot
    from cs_tools.types import SecurityPrincipal


class _UserInfo(TypedDict):
    username: str
    email: str
    display_name: str
    visibility: str  # one of: DEFAULT, NOT_SHAREABLE
    type: str  # principal  # noqa: A003


class _GroupInfo(TypedDict):
    username: str
    email: str
    display_name: str
    visibility: str  # one of: DEFAULT, NOT_SHAREABLE
    type: str  # principal  # noqa: A003


class _AssociationInfo(TypedDict):
    principal_name: str
    principal_type: str
    group_name: str


def _get_current_security(ts: ThoughtSpot) -> tuple[list[_UserInfo], list[_GroupInfo], list[_AssociationInfo]]:
    """ """
    users_and_groups: list[SecurityPrincipal] = ts.api.v1.user_list().json()
    users: list[_UserInfo] = []
    groups: list[_GroupInfo] = []
    associations: list[_AssociationInfo] = []

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
    users: list[_UserInfo], groups: list[_GroupInfo], xref: list[_AssociationInfo]
) -> list[SecurityPrincipal]:
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
