"""
Behavioral spec for scriptability's TML spec-drift resilience.

ThoughtSpot Cloud adds attributes to the TML spec faster than the thoughtspot_tml
library ships spec regenerations (viz_style on TS 26.7, dynamic_title before it --
thoughtspot_tml issues #40 and #29). The library parses strictly, so a single file
carrying an unknown attribute raises TMLDecodeError.

Pins the properties customers depend on:

  1. deploy's file loading collects per-file parse failures instead of letting one
     drifted file crash the entire deploy before anything is sent.

  2. A drift-class failure explains itself: the installed thoughtspot_tml version
     and the unrecognized attribute, so the operator knows the fix is a library
     update -- not a broken file.

  3. Failures that are NOT drift (e.g. YAML syntax errors) are still collected per
     file, with the library's own diagnostic as the reason.

  4. checkpoint detects exported files the installed library cannot parse -- the
     export itself is raw text and always succeeds, so these are landmines that
     only explode at deploy time. They must be flagged at export time.

  5. Failure reporting is capped on the console. A drift event affects every
     object using the new attribute (223 of 2,341 Liveboards in one observed
     case) -- the console gets the first few in detail and a count of the rest,
     while the logfile always receives every failure.
"""

from __future__ import annotations

import importlib.metadata
import logging
import pathlib

from cs_tools.cli.tools.scriptability.app import (
    _FAILURE_DETAIL_LIMIT,
    _find_unparseable_exports,
    _load_tml_files,
    _log_failures_capped,
    _TMLParseFailure,
)
import thoughtspot_tml

GOOD_TABLE_TML = """
guid: 11111111-2222-3333-4444-555555555555
table:
  name: MY_TABLE
  db: MY_DB
  schema: MY_SCHEMA
  db_table: MY_TABLE
"""

# A SERVER-SIDE SPEC ADDITION THE INSTALLED LIBRARY DOES NOT KNOW ABOUT.
DRIFTED_TABLE_TML = GOOD_TABLE_TML + "  viz_style: FANCY\n"

NOT_EVEN_YAML = "table:\n  name: [unclosed\n"


def _write(directory: pathlib.Path, filename: str, text: str) -> pathlib.Path:
    path = directory / filename
    path.write_text(text, encoding="utf-8")
    return path


def test_healthy_files_load_with_no_failures(tmp_path):
    paths = [
        _write(tmp_path, "one.table.tml", GOOD_TABLE_TML),
        _write(tmp_path, "two.table.tml", GOOD_TABLE_TML),
    ]

    loaded, failures = _load_tml_files(paths)

    assert failures == []
    assert [path for path, _ in loaded] == paths
    assert all(tml.guid == "11111111-2222-3333-4444-555555555555" for _, tml in loaded)


def test_a_drifted_file_is_collected_not_raised(tmp_path):
    # ONE FILE WITH A NEWER-THAN-THE-LIBRARY ATTRIBUTE MUST NOT COST THE WHOLE DEPLOY.
    good = _write(tmp_path, "good.table.tml", GOOD_TABLE_TML)
    bad = _write(tmp_path, "bad.table.tml", DRIFTED_TABLE_TML)

    loaded, failures = _load_tml_files([good, bad])

    # THE HEALTHY FILE STILL LOADS.
    assert [path for path, _ in loaded] == [good]

    # THE DRIFTED FILE IS REPORTED, WITH THE LIBRARY'S EXCEPTION ATTACHED.
    assert len(failures) == 1
    assert failures[0].source == str(bad)
    assert isinstance(failures[0].error, thoughtspot_tml.exceptions.TMLDecodeError)


def test_drift_failures_explain_the_library_version_and_attribute(tmp_path):
    # "Unrecognized attribute" ALONE SENDS OPERATORS HUNTING FOR A FILE PROBLEM.
    # THE REASON MUST POINT AT THE ACTUAL FIX: THE INSTALLED LIBRARY IS TOO OLD.
    bad = _write(tmp_path, "bad.table.tml", DRIFTED_TABLE_TML)

    _, failures = _load_tml_files([bad])

    reason = failures[0].reason
    assert "viz_style" in reason
    assert importlib.metadata.version("thoughtspot_tml") in reason
    assert "newer than the installed" in reason


def test_non_drift_decode_failures_are_still_collected_per_file(tmp_path):
    # A BROKEN FILE (HAND-EDIT GONE WRONG) IS COLLECTED LIKE ANY OTHER PARSE FAILURE,
    # AND ITS REASON IS THE LIBRARY'S OWN DIAGNOSTIC -- NOT THE DRIFT HINT.
    good = _write(tmp_path, "good.table.tml", GOOD_TABLE_TML)
    bad = _write(tmp_path, "bad.table.tml", NOT_EVEN_YAML)

    loaded, failures = _load_tml_files([good, bad])

    assert [path for path, _ in loaded] == [good]
    assert len(failures) == 1
    assert failures[0].source == str(bad)
    assert "newer than the installed" not in failures[0].reason
    assert failures[0].reason == str(failures[0].error)


def _export_result(edoc, *, guid: str = "g-1", name: str = "MY_TABLE", type_: str = "table") -> dict:
    return {"edoc": edoc, "info": {"id": guid, "name": name, "type": type_, "status": {"status_code": "OK"}}}


def test_checkpoint_flags_exports_the_installed_library_cannot_parse():
    # EXPORT WRITES RAW TEXT AND SUCCEEDS EVEN WHEN THE EDOC CARRIES DRIFTED ATTRIBUTES.
    # THOSE FILES WILL FAIL EVERY DEPLOY UNTIL THE LIBRARY UPDATES -- SAY SO NOW.
    results = [
        _export_result(GOOD_TABLE_TML),
        _export_result(DRIFTED_TABLE_TML, guid="g-2", name="DRIFTED_TABLE"),
    ]

    landmines = _find_unparseable_exports(results)

    assert len(landmines) == 1
    assert "DRIFTED_TABLE" in landmines[0].source
    assert "g-2" in landmines[0].source
    assert "viz_style" in landmines[0].reason


def test_checkpoint_ignores_exports_that_already_failed():
    # A FAILED EXPORT HAS NO EDOC -- IT IS ALREADY REPORTED AS AN ERROR BY THE EXPORT
    # TABLE AND MUST NOT ALSO BE COUNTED AS A PARSE LANDMINE.
    results = [
        {"edoc": None, "info": {"id": "g-err", "status": {"status_code": "ERROR"}}},
        _export_result(GOOD_TABLE_TML),
    ]

    assert _find_unparseable_exports(results) == []


SCRIPTABILITY_LOGGER = "cs_tools.cli.tools.scriptability.app"


def _drift_failure(i: int) -> _TMLParseFailure:
    error = thoughtspot_tml.exceptions.TMLDecodeError(
        thoughtspot_tml.Table,
        exc=TypeError("__init__() got an unexpected keyword argument 'viz_style'"),
        document="",
    )
    return _TMLParseFailure(source=f"lb-{i}.liveboard.tml", error=error)


def test_a_failure_flood_is_capped_on_the_console(caplog):
    # 223 DRIFTED LIVEBOARDS MUST NOT BECOME 223 CONSOLE LINES. THE CONSOLE HANDLER IS
    # INFO+ AND THE FILE HANDLER IS DEBUG+, SO WARNING/ERROR RECORDS STAND IN FOR CONSOLE
    # LINES AND DEBUG RECORDS FOR THE LOGFILE-ONLY REMAINDER.
    failures = [_drift_failure(i) for i in range(_FAILURE_DETAIL_LIMIT + 3)]

    with caplog.at_level(logging.DEBUG, logger=SCRIPTABILITY_LOGGER):
        _log_failures_capped(failures, level=logging.ERROR, describe=lambda f: f"Could not parse '{f.source}'")

    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == _FAILURE_DETAIL_LIMIT + 1
    assert "..and 3 more, see the logs for the full list." in errors[-1].getMessage()

    # THE LOGFILE RECEIVES EVERY FAILURE EXACTLY ONCE: THE FIRST FEW VIA THEIR CONSOLE
    # RECORDS, THE OVERFLOW VIA DEBUG.
    debugs = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert [r.getMessage() for r in debugs] == [
        f"Could not parse '{f.source}'" for f in failures[_FAILURE_DETAIL_LIMIT:]
    ]


def test_a_handful_of_failures_all_appear_in_detail(caplog):
    # CAPPING ONLY MATTERS AT SCALE -- A COUPLE OF FAILURES GET FULL DETAIL AND NO TALLY.
    failures = [_drift_failure(i) for i in range(2)]

    with caplog.at_level(logging.DEBUG, logger=SCRIPTABILITY_LOGGER):
        _log_failures_capped(failures, level=logging.WARNING, describe=lambda f: f"Exported {f.source}")

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert "..and" not in caplog.text
    assert [r for r in caplog.records if r.levelno == logging.DEBUG] == []
