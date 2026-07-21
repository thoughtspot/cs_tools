"""
Spec for the partial-failure summary the searchable `metadata` command emits.

When fetch skips batches (network failures after retries), the command must surface a loud,
useful summary rather than let an incomplete extract pass silently — and the message must be
strategy-aware, because a TRUNCATE run replaced the target with incomplete data while an
UPSERT run self-heals on the next successful run.
"""

from __future__ import annotations

import logging

from cs_tools.api.workflows.metadata import SkippedSearch
from cs_tools.cli.tools.searchable.app import _report_skipped_searches


def _skips() -> list[SkippedSearch]:
    return [
        SkippedSearch(metadata_type="LOGICAL_COLUMN", identifiers=[f"col-{i}" for i in range(30)], error="ReadTimeout"),
        SkippedSearch(metadata_type="LOGICAL_TABLE", identifiers=["tbl-1", "tbl-2"], error="ReadError"),
    ]


def test_summary_reports_totals_breakdown_and_a_bounded_sample(caplog):
    with caplog.at_level(logging.WARNING):
        _report_skipped_searches(_skips(), is_truncate=False)

    msg = caplog.text
    assert "32 object(s) could not be fetched" in msg  # 30 + 2, not the raw batch count
    assert "LOGICAL_COLUMN: 30 skipped" in msg
    assert "LOGICAL_TABLE: 2 skipped" in msg
    assert "sample:" in msg
    assert "(+27 more)" in msg  # 32 total minus the 5 sampled
    # the full 32-id list is NOT dumped into the console warning
    assert "col-20" not in msg


def test_summary_consequence_is_strategy_aware(caplog):
    with caplog.at_level(logging.WARNING):
        _report_skipped_searches(_skips(), is_truncate=True)
    assert "TRUNCATE" in caplog.text
    assert "REPLACED" in caplog.text

    caplog.clear()

    with caplog.at_level(logging.WARNING):
        _report_skipped_searches(_skips(), is_truncate=False)
    assert "UPSERT/APPEND" in caplog.text
    assert "no data loss" in caplog.text
