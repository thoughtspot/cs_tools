"""
Spec for searchable transformer resilience to omitted timestamps.

ThoughtSpot APIs omit created/modified for some object types (observed: DependentObject 'created'
for FEEDBACK, Group 'modified' for LOCAL_GROUP). cs_tools is a batch extract -- it must store NULL
and keep the row, never crash. Shared coercion lives in validators.utc_from_millis /
validators.ensure_datetime_is_utc (now None-tolerant).
"""

from __future__ import annotations

import datetime as dt

from cs_tools import validators
from cs_tools.cli.tools.searchable import api_transformer as T
from cs_tools.cli.tools.searchable.models import DependentObject

# --- shared coercion --------------------------------------------------------


def test_utc_from_millis_none_is_none():
    assert validators.utc_from_millis(None) is None


def test_utc_from_millis_coerces_epoch_millis():
    got = validators.utc_from_millis(1_700_000_000_000)
    assert got == dt.datetime(2023, 11, 14, 22, 13, 20, tzinfo=dt.timezone.utc)


def test_ensure_datetime_is_utc_tolerates_none():
    # the shared PlainValidator now short-circuits None so every model's validator inherits it
    assert validators.ensure_datetime_is_utc.func(None) is None


# --- dependents: 'created' omitted for FEEDBACK -----------------------------


def _dep_payload(dependents: list[dict], *, dependent_type: str = "ANSWER") -> dict:
    return {"metadata_id": "col-1", "dependent_objects": {"grp": {dependent_type: dependents}}}


def _dependent(**overrides) -> dict:
    base = {"id": "dep-1", "name": "A", "author": "user-1", "created": 1_700_000_000_000, "modified": 1_700_000_000_000}
    base.update(overrides)
    return base


def test_dependent_missing_created_is_kept_with_null():
    good = _dependent(id="dep-good")
    no_created = {k: v for k, v in _dependent(id="dep-feedback").items() if k != "created"}

    rows = T.ts_metadata_dependent([_dep_payload([good, no_created], dependent_type="FEEDBACK")], cluster="cluster-1")
    by_guid = {r["dependent_guid"]: r for r in rows}

    assert set(by_guid) == {"dep-good", "dep-feedback"}
    assert by_guid["dep-feedback"]["created"] is None
    assert by_guid["dep-good"]["created"] is not None


# --- groups (v1): 'modified' omitted for LOCAL_GROUP ------------------------


def _group_v1(**header_overrides) -> dict:
    header = {
        "id": "grp-1",
        "name": "G",
        "displayName": "G",
        "orgIds": [0],
        "created": 1_700_000_000_000,
        "modified": 1_700_000_000_000,
    }
    header.update(header_overrides)
    return {"header": header, "visibility": "SHARABLE", "type": "LOCAL_GROUP"}


def test_group_v1_missing_modified_is_kept_with_null():
    g = _group_v1(id="grp-local")
    del g["header"]["modified"]  # some LOCAL_GROUP records omit 'modified'

    rows = T.to_group_v1([g], cluster="cluster-1")

    assert len(rows) == 1
    assert rows[0]["group_guid"] == "grp-local"
    assert rows[0]["modified"] is None
    assert rows[0]["created"] is not None


# --- models accept null timestamps ------------------------------------------


def test_model_accepts_null_created_and_modified():
    obj = DependentObject(
        cluster_guid="cluster-1",
        dependent_guid="dep-1",
        column_guid="col-1",
        name="A",
        description=None,
        author_guid="user-1",
        created=None,
        modified=None,
        object_type="FEEDBACK",
        object_subtype=None,
        is_verified=False,
        is_version_controlled=False,
    )
    assert obj.created is None
    assert obj.modified is None
