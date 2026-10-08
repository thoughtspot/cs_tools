"""
scriptability's metadata/search transformer: one row per object.

TML export is keyed by GUID and doesn't care about orgs, so we want a single row per object here.
searchable's transformer needs to fan out over metadata_header.orgIds (it fills a per-org table);
we don't - doing that exports the same GUID once for every org it's published to.
"""

from __future__ import annotations

from cs_tools.cli.tools.scriptability import api_transformer as T


def _search_result(**header_overrides) -> dict:
    header = {
        "author": "user-1",
        "created": 1_700_000_000_000,
        "modified": 1_700_000_000_000,
        "aiAnswerGenerationDisabled": False,  # LOGICAL_TABLE needs this for is_sage_enabled
        "orgIds": [0],
    }
    header.update(header_overrides)
    return {
        "metadata_id": "tbl-1",
        "metadata_name": "BRG_USER_GROUPS",
        "metadata_type": "LOGICAL_TABLE",
        "metadata_header": header,
        "metadata_detail": None,
    }


def test_object_published_to_many_orgs_yields_one_row():
    result = _search_result(orgIds=list(range(76)))

    rows = T.ts_metadata_object([result])

    assert len(rows) == 1
    assert rows[0]["object_guid"] == "tbl-1"
    # org_id is gone now - nothing in scriptability ever read it.
    assert "org_id" not in rows[0]


def test_missing_org_ids_still_yields_one_row():
    result = _search_result()
    del result["metadata_header"]["orgIds"]

    rows = T.ts_metadata_object([result])

    assert len(rows) == 1
    assert rows[0]["object_guid"] == "tbl-1"


def test_one_row_per_object_across_a_batch():
    results = [
        _search_result(orgIds=[0, 1, 2]),
        {**_search_result(orgIds=[0, 1]), "metadata_id": "tbl-2", "metadata_name": "OTHER"},
    ]

    rows = T.ts_metadata_object(results)

    assert [r["object_guid"] for r in rows] == ["tbl-1", "tbl-2"]
