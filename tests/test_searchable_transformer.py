"""
Spec for ts_metadata_dependent robustness.

DependentObject requires created/modified/author/name to be non-null, but some dependents come
back from the ThoughtSpot API missing them. The transformer must skip those rows (and count them)
rather than KeyError the whole extract.
"""

from __future__ import annotations

import logging

from cs_tools.cli.tools.searchable.api_transformer import ts_metadata_dependent


def _payload(dependents: list[dict]) -> dict:
    # metadata/search?include_dependent_objects shape: result -> dependent_objects -> {type: [deps]}
    return {"metadata_id": "col-1", "dependent_objects": {"grp": {"ANSWER": dependents}}}


def _dependent(**overrides) -> dict:
    base = {"id": "dep-1", "name": "A", "author": "user-1", "created": 1_700_000_000_000, "modified": 1_700_000_000_000}
    base.update(overrides)
    return base


def test_dependent_missing_required_field_is_skipped_not_crashed(caplog):
    good = _dependent(id="dep-good")
    missing_created = {k: v for k, v in _dependent(id="dep-bad").items() if k != "created"}

    with caplog.at_level(logging.WARNING):
        rows = ts_metadata_dependent([_payload([good, missing_created])], cluster="cluster-1")

    # the good dependent survived; the one missing 'created' was skipped, not raised
    assert [r["dependent_guid"] for r in rows] == ["dep-good"]
    assert "skipped 1 dependent" in caplog.text


def test_all_valid_dependents_are_kept():
    deps = [_dependent(id=f"dep-{i}") for i in range(3)]
    rows = ts_metadata_dependent([_payload(deps)], cluster="cluster-1")
    assert [r["dependent_guid"] for r in rows] == ["dep-0", "dep-1", "dep-2"]
