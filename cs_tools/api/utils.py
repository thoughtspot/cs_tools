from __future__ import annotations

from typing import Any
import logging

log = logging.getLogger(__name__)


def scrub_undefined_sentinel(inp: Any, *, null: Any) -> Any:
    """Recursively remove sentinel values from input parameters."""
    if isinstance(inp, dict):
        return {k: scrub_undefined_sentinel(v, null=null) for k, v in inp.items() if v is not null}

    if isinstance(inp, list):
        return [scrub_undefined_sentinel(v, null=null) for v in inp if v is not null]

    return inp
