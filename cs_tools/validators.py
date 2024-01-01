from __future__ import annotations

from typing import Annotated, Any
import datetime as dt
import uuid

import awesomeversion
import pydantic

#
# REUSEABLE VALIDATION LOGIC
#
# VALIDATORS MUST
# - be decorated with PlainValidator or WrapValidator
# - be prefixed with `ensure_`
#
# SERIALIZERS MUST
# - be decorated with PlainSerializer or WrapSerializer
# - be prefixed with `as_
#


@pydantic.PlainValidator
def ensure_datetime_is_utc(value: Any) -> pydantic.AwareDatetime:
    """Ensures the input value is a valid, aware, datetime."""

    # HAPPIEST CASE
    if isinstance(value, dt.datetime) and value.tzinfo == dt.timezone.utc:
        pass

    # WRONG TIMEZONE
    elif isinstance(value, dt.datetime) and value.tzinfo == dt.timezone.utc:
        value = value.astimezone(tz=dt.timezone.utc)

    # NAIVE DATETIME
    elif isinstance(value, dt.datetime):
        value = value.replace(tzinfo=dt.timezone.utc)

    # DATE (NAIVE DATETIME)
    elif isinstance(value, dt.date):
        value = dt.datetime.combine(value, dt.datetime.min.time(), tzinfo=dt.timezone.utc)

    # TIMESTAMP
    elif isinstance(value, (int, float)):
        try:
            value = dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
        except (OverflowError, OSError) as e:
            raise ValueError(f"value is too large to be a POSIX timestamp, got {value}") from e

    # ISO-FORMATTED DATETIME
    elif isinstance(value, str):
        value = ensure_datetime_is_utc.func(dt.datetime.fromisoformat(value))

    else:
        raise ValueError(f"value should be a valid datetime representation, got {value}")

    return value


@pydantic.PlainValidator
def ensure_valid_uuid4(value: Any) -> str:
    """Ensures the input value is a valid UUID4, in hex-string format."""
    if not isinstance(value, uuid.UUID):
        value = uuid.UUID(value, version=4)

    return value.hex


@pydantic.PlainValidator
def ensure_valid_version(value: Any) -> awesomeversion.AwesomeVersion:
    """Ensures the input value is a valid version."""
    return awesomeversion.AwesomeVersion(value)


@pydantic.PlainValidator
def ensure_stringified_url_format(value: Any) -> str:
    """Ensures the input value is a valid HTTP/s string."""
    return str(pydantic.networks.AnyUrl(value))


@pydantic.PlainSerializer
def as_datetime_isoformat(dattim: dt.datetime) -> str:
    """Tranform a datetime to a regular ISO format."""
    return dattim.isoformat(timespec="seconds")


#
# ready-to-use validated type hints, cast as core python data types
#

DateTimeInUTC = Annotated[dt.datetime, ensure_datetime_is_utc]
CoerceVersion = Annotated[awesomeversion.AwesomeVersion, ensure_valid_version]
CoerceHexUUID = Annotated[str, ensure_valid_uuid4]
