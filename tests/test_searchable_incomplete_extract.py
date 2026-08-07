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


def test_logfile_manifest_enumerates_every_affected_object(caplog):
    # THE CONSOLE BLOCK SAMPLES 3 EXAMPLES PER GROUP ("+N more") -- SUPPORT WORKS FROM THE
    # LOGFILE AND NEEDS THE COMPLETE LIST. A DEBUG RECORD (FILE HANDLER ONLY; CONSOLE IS
    # INFO+) WRITES EVERY IDENTIFIER WITH ITS NAME, GROUPED LIKE THE CONSOLE BLOCK.
    failures = [
        _failure("dependents", "LOGICAL_COLUMN", "col-1", "col-2", "col-3", "col-4", "col-5"),
        _failure("permissions", "ANSWER", "ans-1"),
    ]
    names = {"col-1": "'Revenue' (Sales Fact)", "ans-1": "'Copy of Renewals'"}

    with caplog.at_level(logging.DEBUG):
        _warn_incomplete_extract(failures, load_strategy="TRUNCATE", load_was_skipped=True, names=names)

    debugs = [r.getMessage() for r in caplog.records if r.levelno == logging.DEBUG]
    manifest = next(m for m in debugs if "INCOMPLETE EXTRACT manifest" in m)

    # EVERY IDENTIFIER APPEARS -- INCLUDING THE ONES BEYOND THE CONSOLE'S 3-EXAMPLE CAP.
    for identifier in ("col-1", "col-2", "col-3", "col-4", "col-5", "ans-1"):
        assert identifier in manifest

    # GUID FIRST FOR MACHINE JOINS, NAME ALONGSIDE FOR HUMANS; UNRESOLVED GUIDS STAND ALONE.
    assert "col-1  'Revenue' (Sales Fact)" in manifest
    assert "ans-1  'Copy of Renewals'" in manifest

    # GROUPED ONE-TO-ONE WITH THE CONSOLE BLOCK'S HEADINGS.
    assert "dependents of LOGICAL_COLUMN (5):" in manifest
    assert "permissions of ANSWER (1):" in manifest


def test_manifest_stays_out_of_the_console(caplog):
    # THE MANIFEST MUST NOT UN-SOLVE THE CONSOLE FLOOD -- IT RIDES AT DEBUG, BELOW THE
    # CONSOLE HANDLER'S INFO THRESHOLD. WARNING-LEVEL OUTPUT IS UNCHANGED.
    failures = [_failure("dependents", "LOGICAL_COLUMN", "col-1", "col-2")]

    with caplog.at_level(logging.DEBUG):
        _warn_incomplete_extract(failures, load_strategy="TRUNCATE", load_was_skipped=True)

    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "manifest" not in warnings[0]


def test_examples_show_names_when_the_run_knows_them(caplog):
    # A BARE GUID SENDS THE ADMIN HUNTING; THE RUN ALREADY FETCHED EVERY OBJECT'S NAME
    # BEFORE THE FAILING PHASES, SO THE EXAMPLES CAN SAY WHICH OBJECTS WERE AFFECTED.
    failures = [_failure("dependents", "LOGICAL_COLUMN", "col-1", "col-2")]
    names = {"col-1": "'Revenue' (Sales Fact)"}

    with caplog.at_level(logging.WARNING):
        _warn_incomplete_extract(failures, load_strategy="UPSERT", load_was_skipped=False, names=names)

    assert "'Revenue' (Sales Fact)" in caplog.text
    # AN IDENTIFIER THE RUN NEVER RESOLVED FALLS BACK TO ITS GUID.
    assert "col-2" in caplog.text
