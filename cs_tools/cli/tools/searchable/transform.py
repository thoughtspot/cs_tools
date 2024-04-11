from __future__ import annotations

from typing import Any
import logging

from cs_tools.datastructures import SessionContext
from cs_tools.types import TableRowsFormat

from . import models

log = logging.getLogger(__name__)
ArbitraryJsonFormat = list[dict[str, Any]]


def to_cluster(data: SessionContext) -> TableRowsFormat:
    """
    Extract information from the active session.

    SOURCE: cs_tools.datastructures.SessionContext
    """
    info = models.Cluster.validated_init(
        cluster_guid=data.thoughtspot.cluster_id,
        url=data.thoughtspot.url,
        timezone=data.thoughtspot.timezone,
    )
    return [info.model_dump()]


def to_org(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """
    Simple field renaming.

    SOURCE: /tspublic/v1/orgs
    """
    out: TableRowsFormat = []
    out.append(
        models.Org.validated_init(
            cluster_guid=cluster,
            org_id=data["orgId"],
            name=data["orgName"],
            description=data["description"],
        )
    )
    return [model.model_dump() for model in out]


def to_group(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """
    Mostly simple field renaming, flattening of orgs.

    SOURCE: /tspublic/v1/group
    """
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


def to_group_privilege(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """
    Mostly simple field renaming, flattening of privileges.

    SOURCE: /tspublic/v1/group . privileges
    """
    out: TableRowsFormat = []

    for row in data:
        for privilege in row["privileges"]:
            out.append(
                models.GroupPrivilege.validated_init(
                    cluster_guid=cluster, group_guid=row["header"]["id"], privilege=privilege
                )
            )

    return [model.model_dump() for model in out]


def to_user(data: ArbitraryJsonFormat, ever_seen: set[str], cluster: str) -> TableRowsFormat:
    """
    Mostly simple field renaming.

    SOURCE: /tspublic/v1/user
    """
    out: TableRowsFormat = []

    for row in data:
        if row["header"]["id"] in ever_seen:
            continue

        out.append(
            models.User.validated_init(
                cluster_guid=cluster,
                user_guid=row["header"]["id"],
                username=row["header"]["name"],
                email=row["userContent"]["userProperties"].get("mail"),
                display_name=row["header"]["displayName"],
                sharing_visibility=row["visibility"],
                created=row["header"]["created"] / 1000,
                modified=row["header"]["modified"] / 1000,
                user_type=row["type"],
            )
        )

    return [model.model_dump() for model in out]


def to_org_membership(data: ArbitraryJsonFormat, cluster: str, ever_seen: set[tuple[str, ...]]) -> TableRowsFormat:
    """
    Mostly simple field renaming, flattening of assigned orgs.

    SOURCE: /tspublic/v1/user . orgIds
    """
    out: TableRowsFormat = []

    for row in data:
        for org_id in row["header"]["orgIds"]:
            model = models.OrgMembership.validated_init(
                cluster_guid=cluster, user_guid=row["header"]["id"], org_id=org_id
            )

            if (model.cluster_guid, model.user_guid, str(model.org_id)) in ever_seen:
                continue

            out.append(model)

    return [model.model_dump() for model in out]


def to_group_membership(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """
    Mostly simple field renaming, flattening of assigned groups.

    SOURCE: /tspublic/v1/group . assignedGroups
    """
    out: TableRowsFormat = []

    for row in data:
        for group in row["assignedGroups"]:
            out.append(
                models.GroupMembership.validated_init(
                    cluster_guid=cluster, principal_guid=row["header"]["id"], group_guid=group
                )
            )

    return [model.model_dump() for model in out]


def to_tag(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """
    Mostly simple field renaming, flattening of orgs.

    SOURCE: /tspublic/v1/metadata/list ? type = TAG
    """
    out: TableRowsFormat = []

    for row in data:
        for org_id in row.get("orgIds", [0]):
            out.append(
                models.Tag.validated_init(
                    cluster_guid=cluster,
                    org_id=org_id,
                    tag_guid=row["id"],
                    tag_name=row["name"],
                    color=row.get("clientState", {}).get("color"),
                    author_guid=row["author"],
                    created=row["created"] / 1000,
                    modified=row["modified"] / 1000,
                )
            )

    return [model.model_dump() for model in out]


def to_data_source(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """
    Mostly simple field renaming, flattening of orgs.

    SOURCE: /tspublic/v1/metadata/list ? details = LOGICAL_TABLE
    """
    ever_seen: set[tuple[str]] = set()
    out: TableRowsFormat = []

    for row in data:
        if row.get("metadata_type", None) != "LOGICAL_TABLE":
            continue

        for org_id in row.get("orgIds", [0]):
            model = models.DataSource.validated_init(
                cluster_guid=cluster,
                org_id=org_id,
                data_source_guid=row["data_source"]["id"],
                dbms_type=row["data_source"]["type"],
                name=row["data_source"]["name"],
                description=row["data_source"].get("description"),
            )

            if (model.cluster_guid, str(model.org_id), model.data_source_guid) in ever_seen:
                continue

            ever_seen.add((model.cluster_guid, str(model.org_id), model.data_source_guid))
            out.append(model)

    return [model.model_dump() for model in out]


def to_metadata_object(data: ArbitraryJsonFormat, cluster: str, ever_seen: set[tuple[str, ...]]) -> TableRowsFormat:
    """
    Mostly simple field renaming, flattening of orgs.

    SOURCE: /tspublic/v1/metadata/list ? type = { LOGICAL_TABLE|QUESTION_ANSWER_BOOK|PINBOARD_ANSWER_BOOK }
    """
    out: TableRowsFormat = []

    for row in data:
        for org_id in row.get("orgIds", [0]):
            # NOTE: Sage is only valid on LOGICAL_TABLES as of 9.10.0
            # NOTE: Verification is only valid on Liveboards as of 9.10.0

            model = models.MetadataObject.validated_init(
                cluster_guid=cluster,
                org_id=org_id,
                object_guid=row["id"],
                name=row["name"],
                description=row.get("description"),
                author_guid=row["author"],
                created=row["created"] / 1000,
                modified=row["modified"] / 1000,
                object_type=row["metadata_type"],
                object_subtype=row.get("type", None),
                data_source_guid=row["data_source"]["id"] if "data_source" in row else None,
                is_sage_enabled=not row.get("aiAnswerGenerationDisabled", True),
                is_verified=row.get("isVerified", False) if row["metadata_type"] == "PINBOARD_ANSWER_BOOK" else None,
            )

            if (model.cluster_guid, str(model.org_id), model.object_guid) in ever_seen:
                continue

            out.append(model)

    return [model.model_dump() for model in out]


def to_metadata_column(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """
    Mostly simple field renaming.

    SOURCE: /tspublic/v1/metadata/list ? type = LOGICAL_COLUMN  (cs_tools.middleswares.metadata.columns)
    """
    out: TableRowsFormat = []

    for row in data:
        out.append(models.MetadataColumn.validated_init(cluster_guid=cluster, **row))

    return [model.model_dump() for model in out]


def to_column_synonym(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """
    Clean and de-duplicate synonyms.

    ThoughtSpot does not perform any validation on duplicate column synonyms.

    SOURCE: /tspublic/v1/metadata/list ? type = LOGICAL_COLUMN  (cs_tools.middleswares.metadata.columns)
    """
    ever_seen: set[tuple] = set()
    sanitized: list[models.ColumnSynonym] = []

    for row in data:
        for synonym in row["synonyms"]:
            if synonym is None or not synonym:
                continue

            model = models.ColumnSynonym.validated_init(
                cluster_guid=cluster,
                column_guid=row["column_guid"],
                synonym=synonym,
            )
            unique = tuple(model.model_dump().values())

            if unique in ever_seen:
                log.info(f"Column {model.column_guid} from {row['object_guid']} has duplicate synonym: {model.synonym}")
                continue

            ever_seen.add(unique)
            sanitized.append(model)

    return [row.model_dump() for row in sanitized]


def to_tagged_object(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """
    Mostly simple field renaming.

    SOURCE: /tspublic/v1/metadata/list ? type = TAG
    """
    out: TableRowsFormat = []

    for row in data:
        for tag in row["tags"]:
            out.append(
                models.TaggedObject.validated_init(
                    cluster_guid=cluster,
                    object_guid=row["id"],
                    tag_guid=tag["id"],
                )
            )

    return [model.model_dump() for model in out]


def to_dependent_object(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """
    Mostly simple field renaming.

    SOURCE: /tspublic/v1/dependency/listdependents
    """
    out: TableRowsFormat = []

    for row in data:
        out.append(
            models.DependentObject.validated_init(
                cluster_guid=cluster,
                dependent_guid=row["id"],
                column_guid=row["parent_guid"],
                name=row["name"],
                description=row.get("description"),
                author_guid=row["author"],
                created=row["created"] / 1000,
                modified=row["modified"] / 1000,
                object_type=row["metadata_type"],
                object_subtype=row.get("type", None),
                is_verified=row.get("isVerified", False) if row["metadata_type"] == "PINBOARD_ANSWER_BOOK" else None,
            )
        )

    return [model.model_dump() for model in out]


def to_sharing_access(data: ArbitraryJsonFormat, cluster: str) -> TableRowsFormat:
    """
    Mostly simple field renaming.

    SOURCE: /tspublic/v1/security/metadata/permissions
    """
    out: TableRowsFormat = []

    for row in data:
        PK = (row["object_guid"], row.get("shared_to_user_guid", "NULL"), row.get("shared_to_group_guid", "NULL"))
        out.append(
            models.SharingAccess.validated_init(
                cluster_guid=cluster,
                sk_dummy="-".join(PK),
                object_guid=row["object_guid"],
                shared_to_user_guid=row.get("shared_to_user_guid", None),
                shared_to_group_guid=row.get("shared_to_group_guid", None),
                permission_type=row["permission_type"],
                share_mode=row["share_mode"],
            )
        )

    return [model.model_dump() for model in out]
