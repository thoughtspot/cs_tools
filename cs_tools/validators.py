"""
Reusable validation logic.
"""

from __future__ import annotations

from typing import Annotated, Any
import datetime as dt
import uuid

import awesomeversion
import pydantic

METHOD_CONFIG = pydantic.ConfigDict(arbitrary_types_allowed=True)

# =========================== VALIDATORS ======================================
# - be decorated with PlainValidator or WrapValidator
# - be prefixed with `ensure_`
#


@pydantic.PlainValidator
def ensure_datetime_is_utc(value: Any) -> pydantic.AwareDatetime:
    """Ensures the input value is a valid, aware, datetime."""
    # HAPPIEST CASE
    if (value_is_a_datetime := isinstance(value, dt.datetime)) and value.tzinfo == dt.timezone.utc:
        return value

    # TIMESTAMP (most common case from api)
    elif isinstance(value, (int, float)):
        try:
            return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
        except (OverflowError, OSError) as e:
            raise ValueError(f"value is too large to be a POSIX timestamp, got {value}") from e

    # ISO-FORMATTED DATETIME STRING
    elif isinstance(value, str):
        if value.endswith("Z"):
            value = value.removesuffix("Z")

        value = dt.datetime.fromisoformat(value)
        value_is_a_datetime = True

    #
    # FORMATTED DATETIME.
    #

    # NAIVE DATETIME
    if value_is_a_datetime and value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)

    # WRONG TIMEZONE
    elif value_is_a_datetime and value.tzinfo != dt.timezone.utc:
        return value.astimezone(tz=dt.timezone.utc)

    # DATE (NAIVE DATETIME)
    elif isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.datetime.min.time(), tzinfo=dt.timezone.utc)

    else:
        raise ValueError(f"value should be a valid datetime representation, got {value}")

    assert 1 == 0, "This should be unreachable."


@pydantic.PlainValidator
def ensure_valid_uuid4(value: Any) -> str:
    """Ensures the input value is a valid UUID4, in hex-string format."""
    if not isinstance(value, uuid.UUID):
        value = uuid.UUID(value, version=4)

    return value.hex


@pydantic.PlainValidator
def ensure_url_string(value: Any) -> str:
    """Ensures the input value is a valid HTTP URL."""
    return str(pydantic.AnyHttpUrl(value))


@pydantic.PlainValidator
def ensure_valid_version(value: Any) -> awesomeversion.AwesomeVersion:
    """Ensures the input value is a valid version."""
    return awesomeversion.AwesomeVersion(value)


@pydantic.PlainValidator
def ensure_stringified_url_format(value: Any) -> str:
    """Ensures the input value is a valid HTTP/s string."""
    return str(pydantic.networks.AnyUrl(value))


# =========================== SERIALIZERS =====================================
# - be decorated with PlainSerializer or WrapSerializer
# - be prefixed with `as_
#


@pydantic.PlainSerializer
def as_datetime_isoformat(dattim: dt.datetime) -> str:
    """Tranform a datetime to a regular ISO format."""
    return dattim.isoformat(timespec="seconds")


@pydantic.PlainSerializer
def as_version_string(version: awesomeversion.AwesomeVersion) -> str:
    """Tranform an awesomeversion to a regular format."""
    return str(version)


# =========================== READY-TO-USE TYPE HINTS =========================
# - always wrapped in an Annotated type-hint

DateTimeInUTC = Annotated[dt.datetime, ensure_datetime_is_utc]
CoerceVersion = Annotated[awesomeversion.AwesomeVersion, ensure_valid_version, as_version_string]
CoerceHexUUID = Annotated[str, ensure_valid_uuid4]
AnyHttpURLStr = Annotated[str, ensure_url_string]
