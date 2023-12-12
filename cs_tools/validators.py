from __future__ import annotations

from typing import Any
import datetime as dt
import uuid

import awesomeversion
import pydantic


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
def stringified_uuid4(value: Any) -> str:
    """Ensures the input value is a valid UUID4, in hex-string format."""
    if not isinstance(value, uuid.UUID):
        value = uuid.UUID(value, version=4)

    return value.hex


@pydantic.PlainValidator
def stringified_version(value: Any) -> str:
    """Ensures the input value is a valid version string."""
    return str(awesomeversion.AwesomeVersion(value))


@pydantic.PlainValidator
def stringified_url_format(value: Any) -> str:
    """Ensures the input value is a valid HTTP/s string."""
    return str(pydantic.networks.AnyUrl(value))
