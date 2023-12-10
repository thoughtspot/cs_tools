"""
Utilities for when working with the ThoughtSpot APIs.

These are private because consumers of CS Tools codebase should ideally be
using the cs_tools.api.middlewares or consuming the cs_tools.api._rest_api_v1
directly.
"""
from __future__ import annotations

from typing import Any, Union
import copy
import json
import uuid

UNDEFINED = object()
SYSTEM_USERS = {"system": "System User", "su": "Administrator Super-User", "tsadmin": "Administrator"}


def is_valid_guid(to_test: str) -> bool:
    """
    Determine if value is a valid UUID.

    Parameters
    ----------
    to_test : str
        value to test
    """
    try:
        guid = uuid.UUID(to_test)
    except ValueError:
        return False
    return str(guid) == to_test


def scrub_undefined(inp: Any, *, null: Union[UNDEFINED, None]) -> Any:
    """
    Remove sentinel values from input parameters.

    httpx uses None as a meaningful value in some cases. We use the UNDEFINED object as
    a marker for a default value.
    """
    if isinstance(inp, dict):
        return {k: scrub_undefined(v, null=null) for k, v in inp.items() if v is not null}

    if isinstance(inp, list):
        return [scrub_undefined(v, null=null) for v in inp if v is not null]

    return inp


def scrub_sensitive(request_keywords: dict[str, Any]) -> dict[str, Any]:
    """
    Remove sensitive data for logging. It's a poor man's logging.Filter.

    This is purely here to pop off the password.
    """
    SAFEWORDS = ("password",)

    # don't modify the actual keywords we want to build into the request
    secure = copy.deepcopy({k: v for k, v in request_keywords.items() if k not in ("file", "files")})

    for keyword in ("params", "data", "json"):
        # .params on GET, POST, PUT
        # .data, .json on POST, PUT
        data = secure.get(keyword, None)

        if data is None:
            continue

        for safe_word in SAFEWORDS:
            secure[keyword].pop(safe_word, None)

    return secure


def dumps(inp: Union[list[Any], type[UNDEFINED]]) -> Union[str, type[UNDEFINED]]:
    """
    json.dumps, but passthru our UNDEFINED sentinel.
    """
    if inp is UNDEFINED:
        return inp

    return json.dumps(inp)
