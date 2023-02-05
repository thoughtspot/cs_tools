from typing import List

from cs_tools.types import GUID, RecordsFormat
from cs_tools.errors import ContentDoesNotExist


def _find_all_users_with_access_to_worksheet(guid: GUID, thoughtspot) -> List[RecordsFormat]:
    user_guids = {}

    r = thoughtspot.api.security_metadata_permissions(metadata_type="LOGICAL_TABLE", guids=[guid])
    principals = [principal_guid for data in r.json().values() for principal_guid in data["permissions"]]

    for principal_guid in principals:
        try:
            users = thoughtspot.group.users_in(group_name=principal_guid, is_directly_assigned=False)
        except ContentDoesNotExist:
            users = [thoughtspot.api.user_read(user_guid=principal_guid).json()["header"]]

        for user in users:
            if user["id"] in user_guids:
                continue

            guid = user["id"]
            name = user["name"]
            user_guids[guid] = name

    return [{"guid": guid, "name": name} for guid, name in user_guids.items()]
