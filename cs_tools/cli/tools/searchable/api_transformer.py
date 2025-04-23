from __future__ import annotations

from typing import Any
import datetime as dt
import functools as ft
import itertools as it
import json
import logging
import operator

import awesomeversion

from cs_tools import _types, validators
from cs_tools._types import TableRowsFormat
from cs_tools.datastructures import SessionContext

from . import models

log = logging.getLogger(__name__)
ArbitraryJsonFormat = list[dict[str, Any]]


def ts_cluster(data: SessionContext) -> _types.TableRowsFormat:
    """Rehsapes cs_tools.datastructures.SessionContext -> searchable.models.Cluster."""
    reshaped: _types.TableRowsFormat = []

    reshaped = [
        models.Cluster.validated_init(
            cluster_guid=data.thoughtspot.cluster_id,
            url=data.thoughtspot.url,
            timezone=data.thoughtspot.timezone,
        ).model_dump()
    ]

    return reshaped


def ts_org(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes orgs/search -> searchable.models.Org."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        reshaped.append(
            models.Org.validated_init(
                cluster_guid=cluster,
                org_id=result["id"],
                name=result["name"],
                description=result["description"],
            ).model_dump()
        )

    return reshaped


def ts_user(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes users/search -> searchable.models.User."""
    reshaped: _types.TableRowsFormat = []

    # DEV NOTE: @boonhapus, 2024/11/25
    # Users are unique within a cluster.
    #
    # However clusters with high amounts of users can often batch incorrectly when
    # asking for large RECORD_OFFSETs.
    #
    # We'll account for this 0.0001% bug onccurrence.
    #
    seen: set[str] = set()

    for result in data:
        if (unique := f"{cluster}-{result['id']}") in seen:
            log.warning(f"Duplicate user found '{result['name']}' for USER ({result['id']})")
            continue

        reshaped.append(
            models.User.validated_init(
                cluster_guid=cluster,
                user_guid=result["id"],
                username=result["name"],
                email=result["email"],
                display_name=result["display_name"],
                sharing_visibility=result["visibility"],
                created=result["creation_time_in_millis"] / 1000,
                modified=result["modification_time_in_millis"] / 1000,
                user_type=result["account_type"],
            ).model_dump()
        )

        seen.add(unique)

    return reshaped


def ts_group(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes groups/search -> searchable.models.Group."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        for org in result.get("orgs", None) or [{"id": 0}]:
            reshaped.append(
                models.Group.validated_init(
                    cluster_guid=cluster,
                    org_id=org["id"],
                    group_guid=result["id"],
                    group_name=result["name"],
                    description=result["description"],
                    display_name=result["display_name"],
                    sharing_visibility=result["visibility"],
                    created=result["creation_time_in_millis"] / 1000,
                    modified=result["modification_time_in_millis"] / 1000,
                    group_type=result["type"],
                ).model_dump()
            )

    return reshaped


def to_group_v1(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """Reshapes groups/search -> searchable.models.Group. Needed for V1 API."""
    out: TableRowsFormat = []

    for row in data:
        for org_id in row["header"].get("orgIds", [0]):
            out.append(
                models.Group.validated_init(
                    cluster_guid=cluster,
                    org_id=org_id,
                    group_guid=row["header"]["id"],
                    group_name=row["header"]["name"],
                    description=row["header"].get("description"),
                    display_name=row["header"]["displayName"],
                    sharing_visibility=row["visibility"],
                    created=row["header"]["created"] / 1000,
                    modified=row["header"]["modified"] / 1000,
                    group_type=row["type"],
                )
            )

    return [model.model_dump() for model in out]


def ts_org_membership(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes users/search -> searchable.models.OrgMembership."""
    reshaped: _types.TableRowsFormat = []

    # DEV NOTE: @boonhapus, 2024/11/25
    # Users are unique within a cluster and cannot be assigned multiple times.
    #
    # However clusters with high amounts of users can often batch incorrectly when
    # asking for large RECORD_OFFSETs.
    #
    # We'll account for this 0.0001% bug onccurrence.
    #
    seen: set[str] = set()

    for result in data:
        for org in result.get("orgs", None) or [{"id": 0}]:
            if (unique := f"{cluster}-{result['id']}-{org['id']}") in seen:
                log.warning(f"Duplicate user found '{result['name']}' for USER ({result['id']})")
                continue

            reshaped.append(
                models.OrgMembership.validated_init(
                    cluster_guid=cluster,
                    user_guid=result["id"],
                    org_id=org["id"],
                ).model_dump()
            )

            seen.add(unique)

    return reshaped


def ts_group_membership(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes {groups|users}/search -> searchable.models.GroupMembership."""
    reshaped: _types.TableRowsFormat = []

    # DEV NOTE: @boonhapus, 2024/11/25
    # Users are unique within a cluster.
    #
    # However clusters with high amounts of users can often batch incorrectly when
    # asking for large RECORD_OFFSETs.
    #
    # We'll account for this 0.0001% bug onccurrence.
    #
    seen: set[str] = set()

    for result in data:
        result_is_group = result["parent_type"] == "GROUP"

        # DEV NOTE: @boonhapus, 2024/11/25
        # Here, we are saying "PRINCIPAL is a member of GROUP" and for USER, this can be
        # found by iterating over the User's groups, but for GROUP, we are given its
        # sub-groups instead so we have to reverse the relationship.
        #
        groups = result["sub_groups"] if result_is_group else result["user_groups"]

        for group in groups:
            p_attr = group if result_is_group else result
            g_attr = result if result_is_group else group

            if (unique := f"{cluster}-{p_attr['id']}-{g_attr['id']}") in seen:
                continue

            reshaped.append(
                models.GroupMembership.validated_init(
                    cluster_guid=cluster,
                    principal_guid=p_attr["id"],
                    group_guid=g_attr["id"],
                ).model_dump()
            )

            seen.add(unique)

    return reshaped


def to_group_membership(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """Reshapes {groups|users}/search -> searchable.models.GroupMembership. Needed for V1 API."""
    out: TableRowsFormat = []

    for row in data:
        for group in row["assignedGroups"]:
            out.append(
                models.GroupMembership.validated_init(
                    cluster_guid=cluster, principal_guid=row["header"]["id"], group_guid=group
                )
            )

    return [model.model_dump() for model in out]


def ts_group_privilege(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes {groups|users}/search -> searchable.models.GroupPrivilege."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        for privilege in result["privileges"]:
            reshaped.append(
                models.GroupPrivilege.validated_init(
                    cluster_guid=cluster,
                    group_guid=result["id"],
                    privilege=privilege,
                ).model_dump()
            )

    return reshaped


def to_group_privilege(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """Reshapes {groups|users}/search -> searchable.models.GroupPrivilege. Needed for V1 API."""
    out: TableRowsFormat = []

    for row in data:
        for privilege in row["privileges"]:
            out.append(
                models.GroupPrivilege.validated_init(
                    cluster_guid=cluster, group_guid=row["header"]["id"], privilege=privilege
                )
            )

    return [model.model_dump() for model in out]


def ts_tag(data: list[_types.APIResult], *, cluster: _types.GUID, current_org: int) -> _types.TableRowsFormat:
    """Reshapes {groups|users}/search -> searchable.models.Tag."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        reshaped.append(
            models.Tag.validated_init(
                cluster_guid=cluster,
                org_id=current_org,
                tag_guid=result["id"],
                tag_name=result["name"],
                author_guid=result["author_id"],
                created=result["creation_time_in_millis"] / 1000,
                modified=result["modification_time_in_millis"] / 1000,
                color=result["color"],
            ).model_dump()
        )

    return reshaped


def ts_data_source(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes metadata/search?type=DATA_SOURCE -> searchable.models.DataSource."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        if result["metadata_type"] != "CONNECTION":
            continue

        for org_id in result["metadata_header"].get("orgIds", None) or [0]:
            reshaped.append(
                models.DataSource.validated_init(
                    cluster_guid=cluster,
                    org_id=org_id,
                    data_source_guid=result["metadata_id"],
                    dbms_type=result["metadata_header"]["type"],
                    name=result["metadata_name"],
                    description=result["metadata_header"].get("description", None),
                ).model_dump()
            )

    return reshaped


def ts_metadata_object(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes metadata/search?type={LOGICAL_TABLE|ANSWER|LIVEBOARD} -> searchable.models.MetadataObject."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        if result["metadata_type"] not in ("LOGICAL_TABLE", "ANSWER", "LIVEBOARD"):
            continue

        can_be_sage_enabled = result["metadata_type"] == "LOGICAL_TABLE"
        is_worksheetv2 = result["metadata_header"].get("worksheetVersion") == "V2"

        for org_id in result["metadata_header"].get("orgIds", None) or [0]:
            reshaped.append(
                models.MetadataObject.validated_init(
                    cluster_guid=cluster,
                    org_id=org_id,
                    object_guid=result["metadata_id"],
                    name=result["metadata_name"],
                    description=result["metadata_header"].get("description", None),
                    author_guid=result["metadata_header"]["author"],
                    created=result["metadata_header"]["created"] / 1000,
                    modified=result["metadata_header"]["modified"] / 1000,
                    object_type=result["metadata_type"],
                    object_subtype="MODEL" if is_worksheetv2 else result["metadata_header"].get("type", None),
                    data_source_guid=(result["metadata_detail"] or {}).get("dataSourceId", None),
                    is_sage_enabled=(
                        not result["metadata_header"]["aiAnswerGenerationDisabled"] if can_be_sage_enabled else None
                    ),
                    is_verified=result["metadata_header"].get("isVerified", False),
                    is_version_controlled=result["metadata_header"].get("isVersioningEnabled", False),
                ).model_dump()
            )

    return reshaped


def ts_metadata_tml(
    metadata_info: list[_types.APIResult],
    tml_info: list[_types.APIResult],
    edoc_format: str,
    *,
    cluster: _types.GUID,
    org_id: int,
) -> _types.TableRowsFormat:
    """Reshapes metadata/search and metadata/tml/export -> searchable.models.MetadataTML."""
    reshaped: _types.TableRowsFormat = []

    for result in tml_info:
        # IGNORE ERRORS (which we already alerted about).
        if result["edoc"] is None:
            continue

        # THIS __SHOULD__ BE SAFE , CONSIDERING OUR INPUT TO metadata/tml/export WERE THESE OBJECTS.
        metadata = next(m for m in metadata_info if m["object_guid"] == result["info"]["id"])

        reshaped.append(
            models.MetadataTML.validated_init(
                cluster_guid=cluster,
                org_id=org_id,
                snapshot_date=dt.datetime.now(tz=dt.timezone.utc).date(),
                object_guid=result["info"]["id"],
                name=result["info"]["name"],
                object_type=metadata["object_type"],
                object_subtype=metadata["object_subtype"],
                author_guid=metadata["author_guid"],
                created=metadata["created"],
                modified=metadata["modified"],
                tml_blob=result["edoc"],
                tml_format=edoc_format,
            ).model_dump()
        )

    return reshaped


def ts_tagged_object(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes metadata/search?type={CONNECTION|LOGICAL_TABLE|ANSWER|LIVEBOARD} -> searchable.models.TaggedObject."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        for tag in result["metadata_header"]["tags"]:
            reshaped.append(
                models.TaggedObject.validated_init(
                    cluster_guid=cluster,
                    object_guid=result["metadata_id"],
                    tag_guid=tag["id"],
                ).model_dump()
            )

    return reshaped


def ts_metadata_column(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes metadata/search?type=LOGICAL_TABLE&include_details=True -> searchable.models.MetadataColumn."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        for column in result["metadata_detail"]["columns"]:
            reshaped.append(
                models.MetadataColumn.validated_init(
                    cluster_guid=cluster,
                    column_guid=column["header"]["id"],
                    object_guid=result["metadata_id"],
                    column_name=column["header"]["name"],
                    description=column["header"].get("description", None),
                    data_type=column["dataType"],
                    column_type=column["type"],
                    additive=column["isAdditive"],
                    aggregation=column["defaultAggrType"],
                    hidden=column["header"]["isHidden"],
                    index_type=column["indexType"],
                    geo_config=column.get("geoConfig", {}).get("type", None),
                    index_priority=column["indexPriority"],
                    format_pattern=column.get("formatPattern", None),
                    currency_type=column.get("currencyTypeInfo", {}).get("setting", None),
                    attribution_dimension=column["isAttributionDimension"],
                    spotiq_preference=column["spotiqPreference"] == "DEFAULT",
                    calendar_type=column.get("calendarTableGUID", None),
                    is_formula="formulaId" in column,
                ).model_dump()
            )

    return reshaped


def ts_column_synonym(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes metadata/search?type=LOGICAL_TABLE&include_details=True -> searchable.models.ColumnSynonym."""
    reshaped: _types.TableRowsFormat = []

    # DEV NOTE: @boonhapus, 2024/11/25
    # The ThoughtSpot column settings UI exposes a freeform field for synonyms.
    # No validation is performed, so it's possible for a User to define an
    # identical synonym multiple times.
    #
    seen: set[str] = set()

    for result in data:
        for column in result["metadata_detail"]["columns"]:
            for synonym in column["synonyms"]:
                if (unique := f"{column['header']['id']}-{synonym}") in seen:
                    log.warning(f"Duplicate synonym found '{synonym}' for COLUMN ({column['header']['id']})")
                    continue

                reshaped.append(
                    models.ColumnSynonym.validated_init(
                        cluster_guid=cluster,
                        column_guid=column["header"]["id"],
                        synonym=synonym,
                    ).model_dump()
                )

                seen.add(unique)

    return reshaped


def ts_metadata_dependent(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes metadata/search?type=LOGICAL_COLUMN&include_dependent_objects=True -> searchable.models.MetadataObject."""  # noqa: E501
    reshaped: _types.TableRowsFormat = []

    for result in data:
        for dependents_info in result["dependent_objects"].values():
            for dependent_type, dependents in dependents_info.items():
                for dependent in dependents:
                    reshaped.append(
                        # DEV NOTE: @boonhapus, 2024/12/06
                        # There are typically an order of magnitude MORE dependents than anything else in ThoughtSpot
                        # so we'll trust most of the fields coming back from the ThoughtSpot API and only validate the
                        # complex_types.
                        {
                            "cluster_guid": cluster,
                            "dependent_guid": dependent["id"],
                            "column_guid": result["metadata_id"],
                            "name": dependent["name"],
                            "description": dependent.get("description", None),
                            "author_guid": dependent["author"],
                            "created": validators.ensure_datetime_is_utc.func(dependent["created"] / 1000),
                            "modified": validators.ensure_datetime_is_utc.func(dependent["modified"] / 1000),
                            "object_type": dependent_type,
                            "object_subtype": dependent.get("type", None),
                            "is_verified": dependent.get("isVerified", False),
                            "is_version_controlled": dependent.get("isVersioningEnabled", False),
                        }
                    )

    return reshaped


def ts_metadata_permissions(
    data: list[_types.APIResult],
    *,
    compat_ts_version: awesomeversion.AwesomeVersion,
    compat_all_group_guids: set[_types.GUID],
    cluster: _types.GUID,
    permission_type: _types.ShareType = "DEFINED",
) -> _types.TableRowsFormat:
    """Reshapes security/metadata/fetch-permissions -> searchable.models.SharingAccess."""
    reshaped: _types.TableRowsFormat = []

    for result in data:
        if compat_ts_version < "10.3.0":
            # DEV NOTE: @boonhapus, 2024/11/25
            # THE RESPONSE PAYLOAD WAS DIFFERENT IN V1 API. ONCE WE HIT 10.3.0 n-2 for
            # SW, WE CAN REMOVE THIS AND THE COMPATs.
            #
            for metadata_guid, access_info in result.items():
                for principal_id, access in access_info["permissions"].items():
                    is_group_share = principal_id in compat_all_group_guids
                    is_user_share = not is_group_share

                    reshaped.append(
                        {
                            "cluster_guid": cluster,
                            "sk_dummy": "-".join([metadata_guid, principal_id]),
                            "object_guid": metadata_guid,
                            "shared_to_user_guid": principal_id if is_user_share else None,
                            "shared_to_group_guid": principal_id if is_group_share else None,
                            "permission_type": permission_type,
                            "share_mode": access["shareMode"],
                            "share_type": None,
                        }
                    )

        else:
            # V2 API DATA TRANSFORMER
            for object_details in result["metadata_permission_details"]:
                # DEV NOTE: @boonhapus, 2024/11/24
                # TBTH, I'M NOT SURE HOW THIS EVEN HAPPENS...
                #
                if not object_details:
                    continue

                is_column_level_security = object_details["metadata_type"] == "LOGICAL_COLUMN"

                for access_info in object_details.get("principal_permission_info", []):
                    for access in access_info["principal_permissions"]:
                        is_group_share = access_info["principal_type"] == "USER_GROUP"
                        is_user_share = access_info["principal_type"] == "USER"

                        reshaped.append(
                            {
                                "cluster_guid": cluster,
                                "sk_dummy": "-".join([object_details["metadata_id"], access["principal_id"]]),
                                "object_guid": object_details["metadata_id"],
                                "shared_to_user_guid": access["principal_id"] if is_user_share else None,
                                "shared_to_group_guid": access["principal_id"] if is_group_share else None,
                                "permission_type": permission_type,
                                "share_mode": access["permission"],
                                "share_type": "COLUMN_LEVEL_SECURITY"
                                if is_column_level_security
                                else "OBJECT_LEVEL_SECURITY",
                            }
                        )

    return reshaped


def ts_bi_server(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes /searchdata -> searchable.models.BIServer."""
    reshaped: _types.TableRowsFormat = []

    PARTITION_KEY = ft.partial(lambda r: r["Timestamp"].date())
    CLUSTER_KEY = ("Timestamp", "Incident Id", "Viz Id")

    # KEEP TRACK OF DUPLICATE ROWS DUE TO DATA MANAGEMENT ISSUES.
    seen: set[str] = set()

    # ENSURE ALL DATA IS IN UTC PRIOR TO GENERATING ROW_NUMBERS.
    data = [{**row, "Timestamp": validators.ensure_datetime_is_utc.func(row["Timestamp"])} for row in data]

    # SORT PRIOR TO GROUP BY SO WE MAINTAIN CLUSTERING KEY SEMANTICS
    data.sort(key=operator.itemgetter(*CLUSTER_KEY))

    for row_date, rows in it.groupby(data, key=PARTITION_KEY):
        # MANUAL ENUMERATION BECAUSE WE NEED TO ACCOUNT FOR DEDUPLICATION.
        row_number = 0

        for row in rows:
            if (unique := f"{row['Timestamp']}-{row['Incident Id']}-{row['Viz Id']}") in seen:
                continue

            row_number += 1

            reshaped.append(
                models.BIServer.validated_init(
                    **{
                        "cluster_guid": cluster,
                        "sk_dummy": f"{cluster}-{row_date}-{row_number}",
                        "org_id": row.get("Org Id", 0),
                        "incident_id": row["Incident Id"],
                        "timestamp": row["Timestamp"],
                        "url": row["URL"],
                        "http_response_code": row["HTTP Response Code"],
                        "browser_type": row["Browser Type"],
                        "browser_version": row["Browser Version"],
                        "client_type": row["Client Type"],
                        "client_id": row["Client Id"],
                        "answer_book_guid": row["Answer Book GUID"],
                        "viz_id": row["Viz Id"],
                        "user_id": row["User Id"],
                        "user_action": row["User Action"],
                        "query_text": row["Query Text"],
                        "response_size": row["Total Response Size"],
                        "latency_us": row["Total Latency (us)"],
                        "impressions": row["Total Impressions"],
                    }
                ).model_dump()
            )

            seen.add(unique)

    return reshaped


def ts_audit_logs(data: list[_types.APIResult], *, cluster: _types.GUID) -> _types.TableRowsFormat:
    """Reshapes logs/fetch -> searchable.models.AuditLogs."""
    reshaped: _types.TableRowsFormat = []

    # DEV NOTE: @boonhapus, 2024/11/25
    # THOUGHTSPOT SEARCH DATA API SEEMS TO HAVE ISSUES WITH TIMEZONES AND THAT
    # CAUSES DUPLICATION OF DATA.
    #
    seen: set[str] = set()

    # PARTITION_KEY = ...   IS NOT NEEDED BECAUSE THE DATA IS NATURALLY PARTITIONED BY DATE ALREADY.
    CLUSTER_KEY = ("timestamp", "sk_dummy")

    for rows in data:
        assert isinstance(rows, list), "Data returned from the Audit Logs API is not an array[mapping<str, Any>]"

        for row in rows:
            assert isinstance(row, dict), "Data returned from the Audit Logs API is not an array[mapping<str, Any>]"

            d = json.loads(row["log"])

            if (unique := f"{cluster}-{d['id']}") in seen:
                continue

            reshaped.append(
                models.AuditLogs.validated_init(
                    **{
                        "cluster_guid": cluster,
                        "org_id": d["orgId"],
                        "sk_dummy": unique,
                        "timestamp": row["date"],
                        "log_type": d["type"],
                        "user_guid": d["userGUID"],
                        "description": d["desc"],
                        "details": json.dumps(d["data"]),
                    }
                ).model_dump()
            )

            seen.add(unique)

    # SORT AFTER TRANSFORM SO WE HAVE ACCESS TO THE SK.
    reshaped.sort(key=operator.itemgetter(*CLUSTER_KEY))

    return reshaped
