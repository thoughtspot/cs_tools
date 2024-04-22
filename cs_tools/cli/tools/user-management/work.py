from __future__ import annotations

from typing import TYPE_CHECKING
import collections
import datetime as dt
import json
import pathlib

from cs_tools.updater import cs_tools_venv

from . import models

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot
    from cs_tools.types import SecurityPrincipal


def _get_current_security(
    ts: ThoughtSpot,
) -> tuple[list[models.AuthUser], list[models.AuthGroup], list[models.AuthGroupMembership]]:
    """ """
    users_and_groups: list[SecurityPrincipal] = ts.api.v1.user_list().json()
    users: list[models.AuthUser] = []
    groups: list[models.AuthGroup] = []
    associations: list[models.AuthGroupMembership] = []

    for principal in users_and_groups:
        data = {
            "display_name": principal["displayName"],
            "sharing_visibility": principal["visibility"],
        }

        if "USER" in principal["principalTypeEnum"]:
            type_ = "USER"
            users.append(
                {
                    "username": principal["name"],
                    "email": principal["mail"],
                    "user_type": principal["principalTypeEnum"],
                    **data,
                }
            )

        if "GROUP" in principal["principalTypeEnum"]:
            type_ = "GROUP"
            groups.append(
                {
                    "group_name": principal["name"],
                    "description": principal.get("description"),
                    "group_type": principal["principalTypeEnum"],
                    **data,
                }
            )

        for group in principal["groupNames"]:
            associations.append({"principal_name": principal["name"], "principal_type": type_, "group_name": group})

    return users, groups, associations


def _form_principals(
    users: list[models.AuthUser], groups: list[models.AuthGroup], xref: list[models.AuthGroupMembership]
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
                "principalTypeEnum": group["group_type"],
                "groupNames": principals_groups[group["group_name"]],
                "visibility": group["sharing_visibility"],
            }
        )

    for user in users:
        principals.append(
            {
                "name": user["username"],
                "displayName": user["display_name"],
                "mail": user["email"],
                "principalTypeEnum": user["user_type"],
                "groupNames": principals_groups[user["username"]],
                "visibility": user["sharing_visibility"],
            }
        )

    return principals


def _backup_security(data) -> None:
    filename = f"user-sync-{dt.datetime.now(tz=dt.timezone.utc):%Y%m%dT%H%M%S}"

    with pathlib.Path(cs_tools_venv.app_dir / ".cache" / f"{filename}.json").open("w") as f:
        json.dump(data, f, indent=4)
