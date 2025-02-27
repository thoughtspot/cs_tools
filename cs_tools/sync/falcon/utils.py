from __future__ import annotations

from typing import Any, cast
import datetime as dt
import json

import sqlmodel

from cs_tools import _types
from cs_tools.thoughtspot import ThoughtSpot

FMT_TSLOAD_DATETIME = "%Y-%m-%d %H:%M:%S"


def check_if_keyword_needed() -> ThoughtSpot:
    """Determine if Syncer is being instantiated by CS Tools."""
    try:
        import click

        ctx = click.get_current_context().find_root()
        assert ctx.command.name == "cs_tools", "This is not a CS Tools execution, forcing keyword argumentation."

    except (ModuleNotFoundError, AssertionError):
        raise ValueError("missing required keyword-argument 'thoughtspot'") from None

    # THIS WILL GET SET UP PRIOR TO USER-CODE EXECUTION.
    return cast(ThoughtSpot, None)  # LOL :~) we're lying to mypy because this is a hack, ok pls get over it


def clean_datetime(object_: Any) -> str:
    """Convert an arbitrary object into a JSON string."""
    if isinstance(object_, dt.datetime):
        return object_.strftime(FMT_TSLOAD_DATETIME)

    if isinstance(object_, sqlmodel.SQLModel):
        return json.dumps(object_.model_dump())

    return json.dumps(object_)


def roundtrip_json_for_falcon(data: _types.TableRowsFormat) -> _types.TableRowsFormat:
    """
    Round-trip from JSON to sanitize.

    Falcon accepts datetimes in a specific format.
    """
    return json.loads(json.dumps(data, default=clean_datetime))
