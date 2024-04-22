from __future__ import annotations

from typing import Any
import json
import logging
import pathlib

from fastapi import Body, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

from cs_tools import utils

log = logging.getLogger(__name__)
HERE = pathlib.Path(__file__).parent
_scoped = {}

web_app = FastAPI()
web_app.mount("/static", StaticFiles(directory=f"{HERE}/static"), name="static")
templates = Jinja2Templates(directory=f"{HERE}/static")


#
# MAIN WEB APPLICATION
#


@web_app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    data = {
        "request": request,
        "host": _scoped["ts"].session_context.thoughtspot.url,
        "user": _scoped["ts"].session_context.user.display_name,
    }
    return templates.TemplateResponse("index.html", data)


#
# REST API SHIM
#
#  NOTE:
#    The primary goal of cs_tools is to be as no-nonsense as possible. Navigating CORS
#    restrictions, while not incredibly difficult, can get fairly involved based on the
#    client's network architecture.
#
#    By allowing the frontend to talk to the internal python API, we bypass the need to
#    have the browser calling the ThoughtSpot server directly.
#


@web_app.post("/api/security/share")
async def _(type: str = Body(...), guids: list[str] = Body(...), permissions: dict[str, Any] = Body(...)):  # noqa: A002
    """
    TSSetPermissionRequest
    """
    permissions = {guid: data["shareMode"] for guid, data in permissions.items()}
    r = _scoped["ts"].api.v1.security_share(metadata_type=type, guids=guids, permissions=permissions)

    try:
        return r.json()
    except json.JSONDecodeError:
        pass


@web_app.post("/api/defined_permission")
# async def _(request: Request):  # could also do it like this ... how lazy to be?
async def _(type: str = Body(...), guids: list[str] = Body(...)):  # noqa: A002
    """
    TSGetTablePermissionsRequest
    """
    defined_permissions = {column_guid: {"permissions": {}} for column_guid in guids}

    for chunk in utils.batched(guids, n=15):
        r = _scoped["ts"].api.v1.security_metadata_permissions(metadata_type=type, guids=list(chunk))

        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            log.error(f"Could not fetch permissions for type={type}, guids={','.join(chunk)}")
            continue

        # COMBINE THE CHUNKS TOGETHER
        for column_guid, permissions in r.json().items():
            for principal_guid, permission_data in permissions["permissions"].items():
                defined_permissions[column_guid]["permissions"][principal_guid] = permission_data

    return defined_permissions


@web_app.get("/api/list_columns/{guid}")
async def _(guid: str):
    """
    TSGetColumnsRequest
    """
    return _scoped["ts"].logical_table.columns(guids=[guid])


@web_app.get("/api/user_groups")
async def _():
    """
    TSGetUserGroupsRequest
    """
    r = _scoped["ts"].api.v1.metadata_list(
        metadata_type="USER_GROUP", category="ALL", sort="DEFAULT", offset=-1, auto_created=False
    )
    return r.json()


@web_app.get("/api/tables")
async def _():
    """
    TSGetTablesRequest
    """
    r = _scoped["ts"].api.v1.metadata_list(metadata_type="LOGICAL_TABLE", subtypes=["ONE_TO_ONE_LOGICAL"])
    return r.json()
