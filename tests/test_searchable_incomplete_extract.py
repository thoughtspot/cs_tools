"""
Spec for the INCOMPLETE EXTRACT summary block.

The same LOGICAL_COLUMN objects appear in three different fetch phases (details, dependents,
column access), so a breakdown by object type alone cannot say WHAT was lost. And file syncers
(csv, excel, ...) rewrite their output wholesale on every run -- "a later run will fill in the
gaps" only describes database load strategies.
"""

from __future__ import annotations

import logging

from cs_tools.api.workflows.metadata import FetchFailure
from cs_tools.cli.tools.searchable.app import _warn_incomplete_extract
import httpx

ANY_ERROR = httpx.ReadTimeout("simulated slow endpoint")


def _failure(fetched: str, metadata_type: str, *guids: str) -> FetchFailure:
    return FetchFailure(metadata_type=metadata_type, identifiers=guids, error=ANY_ERROR, fetched=fetched)


def test_breakdown_names_the_kind_of_fetch_per_line(caplog):
    failures = [
        _failure("dependents", "LOGICAL_COLUMN", "col-1", "col-2"),
        _failure("permissions", "LOGICAL_TABLE", "tbl-1"),
    ]

    with caplog.at_level(logging.WARNING):
        _warn_incomplete_extract(failures, load_strategy="UPSERT", load_was_skipped=False)

    assert "dependents of LOGICAL_COLUMN" in caplog.text
    assert "permissions of LOGICAL_TABLE" in caplog.text


def test_file_syncers_are_told_to_rerun_not_promised_a_merge(caplog):
    # FILE SYNCERS HAVE NO LOAD STRATEGY -- EVERY RUN REWRITES THE FILES WHOLESALE, SO
    # NOTHING EVER "FILLS IN" GAPS.
    failures = [_failure("dependents", "LOGICAL_COLUMN", "col-1")]

    with caplog.at_level(logging.WARNING):
        _warn_incomplete_extract(failures, load_strategy=None, load_was_skipped=False)

    assert "Re-run to produce a complete extract." in caplog.text
    assert "fill in the gaps" not in caplog.text
