from __future__ import annotations

from typing import TYPE_CHECKING, Any
import datetime as dt
import json

import sqlmodel

from cs_tools.const import FMT_TSLOAD_DATETIME

if TYPE_CHECKING:
    from cs_tools.sync.types import TableRows
    from cs_tools.thoughtspot import ThoughtSpot


def maybe_fetch_from_context() -> ThoughtSpot:
    """Attempt to fetch the ThoughtSpot object."""
    try:
        import click

        context = click.get_current_context()
        thoughtspot = context.obj.thoughtspot

    except ModuleNotFoundError:
        raise ValueError("missing required keyword-argument 'thoughtspot'") from None

    except AttributeError:
        raise ValueError("could not fetch 'thoughtspot' from execution context") from None

    return thoughtspot


def clean_datetime(object_: Any) -> str:
    """Convert an arbitrary object into a JSON string."""
    if isinstance(object_, dt.datetime):
        return object_.strftime(FMT_TSLOAD_DATETIME)

    if isinstance(object_, sqlmodel.SQLModel):
        return json.dumps(object_.model_dump())

    return json.dumps(object_)


def roundtrip_json_for_falcon(data: TableRows) -> TableRows:
    """
    Round-trip from JSON to sanitize.

    Falcon accepts datetimes in a specific format.
    """
    return json.loads(json.dumps(data, default=clean_datetime))
