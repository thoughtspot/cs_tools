import enum


class GUID(str):
    """
    Purely for the sake of annotation documentation.
    """


class AccessLevel(enum.Enum):
    no_access = 'NO_ACCESS'
    read_only = 'READ_ONLY'
    modify = 'MODIFY'


class Principal(enum.Enum):
    user = 'USER'
    group = 'USER_GROUP'


class Privilege(enum.Enum):
    innate = 'AUTHORING'
    can_administer_thoughtspot = 'ADMINISTRATION'
    can_upload_user_data = 'USERDATAUPLOADING'
    can_download_data = 'DATADOWNLOADING'
    can_share_with_all_users = 'SHAREWITHALL'
    can_manage_data = 'DATAMANAGEMENT'
    can_use_experimental_features = 'EXPERIMENTALFEATUREPRIVILEG'
    can_invoke_custom_r_analysis = 'RANALYSIS'
    can_schedule_pinboards = 'JOBSCHEDULING'
    has_spotiq_privilege = 'A3ANALYSIS'
    can_administer_and_bypass_rls = 'BYPASSRLS'

    # Available in ts-sw>=7.0.0 and ts-cloud>=7.0.0
    developer = 'DEVELOPER'
    cannot_create_or_delete_pinboards = 'DISABLE_PINBOARD_CREATION'


class MetadataObject(enum.Enum):
    data_source = 'DATA_SOURCE'
    logical_relationship = 'LOGICAL_RELATIONSHIP'
    saved_answer = 'QUESTION_ANSWER_BOOK'
    pinboard = 'PINBOARD_ANSWER_BOOK'
    tag = 'TAG'

    # table-column or formula
    logical_column = 'LOGICAL_COLUMN'
    # see: MetadataObjectSubtype
    logical_table = 'LOGICAL_TABLE'

    # not currently shown in the Swagger UI.
    group = 'USER_GROUP'
    user = 'USER'


class MetadataObjectSubtype(enum.Enum):
    system_table = 'ONE_TO_ONE_LOGICAL'
    user_upload = 'USER_DEFINED'
    worksheet = 'WORKSHEET'
    view = 'AGGR_WORKSHEET'
    formula = 'FORMULA'
    materialized_view = 'MATERIALIZED_VIEW'
    custom_calendar = 'CALENDAR_TABLE'
    custom_calendar_type = 'CALENDAR_TYPE'
    sql_view = 'SQL_VIEW'


class MetadataCategory(enum.Enum):
    all = 'ALL'
    my = 'MY'
    favorite = 'FAVORITE'
    requested = 'REQUESTED'


class SortOrder(enum.Enum):
    default = 'DEFAULT'
    name = 'NAME'
    display_name = 'DISPLAY_NAME'
    author = 'AUTHOR'
    created = 'CREATED'
    modified = 'MODIFIED'


class ResultsFormat(enum.Enum):
    records = 'FULL'
    values = 'COMPACT'


class PermissionType(enum.Enum):
    inherited = 'EFFECTIVE'
    explicit = 'DEFINED' 


class TMLType(enum.Enum):
    json = 'JSON'
    yaml = 'YAML'


class TMLImportPolicy(enum.Enum):
    partial = 'PARTIAL'
    all_or_none = 'ALL_OR_NONE'
    validate_only = 'VALIDATE_ONLY'


class TMLContentType(enum.Enum):
    table = 'table'
    worksheet = 'worksheet'
    liveboard = 'liveboard'  # currently (as of 8.2) this will be pinboard, but future proofing.
    pinboard = 'pinboard'
    answer = 'answer'
    view = 'sql_view'


class DownloadableContent(enum.Enum):
    saved_answer = 'QUESTION_ANSWER_BOOK'
    pinboard = 'PINBOARD_ANSWER_BOOK'
    logical_table = 'LOGICAL_TABLE'
    data_source = 'DATA_SOURCE'
