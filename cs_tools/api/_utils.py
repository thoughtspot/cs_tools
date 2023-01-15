"""
Utilities for when working with the ThoughtSpot APIs.

These are private because consumers of CS Tools codebase should ideally be
using the cs_tools.api.middlewares or consuming the cs_tools.api._rest_api_v1
directly.
"""
from typing import Any
import uuid
import json
import copy

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


def scrub_undefined(inp: Any) -> Any:
    """
    Remove sentinel values from input parameters.

    httpx uses None as a meaningful value in some cases. We use the UNDEFINED object as
    a marker for a default value.
    """
    if isinstance(inp, dict):
        return {k: scrub_undefined(v) for k, v in inp.items() if v is not UNDEFINED}

    if isinstance(inp, list):
        return [scrub_undefined(v) for v in inp if v is not UNDEFINED]

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
        for safe_word in SAFEWORDS:
            secure.get(keyword, {}).pop(safe_word, None)

    return secure


def dumps(inp: list[Any] | type[UNDEFINED]) -> str | type[UNDEFINED]:
    """
    json.dumps, but passthru our UNDEFINED sentinel.
    """
    if inp is UNDEFINED:
        return inp

    return json.dumps(inp)


def before_version(version: str, compare_to_version: str) -> bool:
    """
    Returns True of the version is earlier than the comparison version.  Only the first two parts are examined.

    It's assumed that there are always two parts.

    Examples:
        8.2 is before 8.9
        8.2 is not before 8.2.3
    """
    v_major, v_minor, *other = version.split(".")
    ct_major, ct_minor, *other = compare_to_version.split(".")

    return v_major < ct_major or (v_major == ct_major and v_minor < ct_minor)
