from typing import List
import enum

from pydantic import BaseModel


class PrivilegeEnum(str, enum.Enum):
    innate = 'AUTHORING'
    can_administer_thoughtspot = 'ADMINISTRATION'
    can_upload_user_data = 'USERDATAUPLOADING'
    can_download_data = 'DATADOWNLOADING'
    can_manage_data = 'DATAMANAGEMENT'
    can_share_with_all_users = 'SHAREWITHALL'
    has_spotiq_privilege = 'A3ANALYSIS'
    can_use_experimental_features = 'EXPERIMENTALFEATUREPRIVILEG'
    can_administer_and_bypass_rls = 'BYPASSRLS'
    can_invoke_custom_r_analysis = 'RANALYSIS'
    cannot_create_or_delete_pinboards = 'DISABLE_PINBOARD_CREATION'


class User(BaseModel):
    guid: str
    name: str
    display_name: str
    email: str
    privileges: List[PrivilegeEnum]
