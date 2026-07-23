"""
Spec for deploy's TML-import result reporting.

The metadata/tml/import response is positionally 1:1 with the submitted TMLs, but each entry's
`request_index` is a server-side ordinal that can exceed len(tmls) -- so it must NOT be used to
index into tmls. Doing so raised IndexError and crashed deploy after a successful import.
"""

from __future__ import annotations

from types import SimpleNamespace
import logging

from cs_tools.cli.tools.searchable.app import _report_tml_import_results


def _tml(name: str, type_name: str = "TABLE") -> SimpleNamespace:
    return SimpleNamespace(name=name, tml_type_name=type_name)


def _result(status_code: str, request_index: int) -> dict:
    return {"request_index": request_index, "response": {"status": {"status_code": status_code}}}


def test_reporting_ignores_sparse_request_index_and_does_not_indexerror(caplog):
    tmls = [_tml("t0"), _tml("t1"), _tml("t2")]
    # request_index values that overrun a 3-element list -- the shape observed from the server
    results = [_result("OK", 0), _result("OK", 16), _result("OK", 56)]

    with caplog.at_level(logging.INFO):
        _report_tml_import_results(tmls, results)  # must not raise IndexError

    # positional pairing: each tml is reported in submission order, regardless of request_index
    assert "TABLE 't0' successfully imported" in caplog.text
    assert "TABLE 't1' successfully imported" in caplog.text
    assert "TABLE 't2' successfully imported" in caplog.text


def test_non_ok_status_is_not_reported_as_success(caplog):
    tmls = [_tml("good"), _tml("bad")]
    results = [_result("OK", 0), _result("ERROR", 9)]

    with caplog.at_level(logging.INFO):
        _report_tml_import_results(tmls, results)

    assert "TABLE 'good' successfully imported" in caplog.text
    assert "'bad' successfully imported" not in caplog.text
